//! Exact local exclusions, no index/config/global-ignore mutation.
use crate::{Result, fs, process};
use std::ffi::OsString;
use std::os::unix::ffi::OsStringExt;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::Duration;

fn run(root: &Path, args: &[&std::ffi::OsStr]) -> Result<process::Output> {
    let mut command = Command::new("git");
    for (key, _) in std::env::vars_os() {
        if key.to_string_lossy().starts_with("GIT_") {
            command.env_remove(key);
        }
    }
    command
        .env("GIT_OPTIONAL_LOCKS", "0")
        .env("GIT_TERMINAL_PROMPT", "0")
        .env("LC_ALL", "C")
        .args([
            "--literal-pathspecs",
            "-c",
            "core.quotepath=false",
            "-c",
            "core.fsmonitor=false",
            "-C",
        ])
        .arg(root)
        .args(args);
    process::run(&mut command, None, true, Some(Duration::from_secs(5)))
}
fn checked(root: &Path, args: &[&str]) -> Result<Vec<u8>> {
    let args: Vec<_> = args.iter().map(std::ffi::OsStr::new).collect();
    let output = run(root, &args)?;
    if !output.status.success() {
        return Err("Git repository/exclusion lookup failed; usage disabled".into());
    }
    Ok(output.stdout)
}
fn path_output(bytes: &[u8]) -> Result<PathBuf> {
    let bytes = bytes.strip_suffix(b"\n").unwrap_or(bytes);
    if !bytes.starts_with(b"\"") {
        return Ok(PathBuf::from(OsString::from_vec(bytes.to_vec())));
    }
    if !bytes.ends_with(b"\"") {
        return Err("invalid quoted Git path".into());
    }
    let mut value = Vec::new();
    let mut i = 1;
    while i < bytes.len() - 1 {
        let c = bytes[i];
        i += 1;
        if c != b'\\' {
            value.push(c);
            continue;
        }
        let c = *bytes.get(i).ok_or("invalid Git escape")?;
        i += 1;
        match c {
            b'\\' | b'"' => value.push(c),
            b'n' => value.push(b'\n'),
            b'r' => value.push(b'\r'),
            b't' => value.push(b'\t'),
            b'a' => value.push(7),
            b'b' => value.push(8),
            b'v' => value.push(11),
            b'f' => value.push(12),
            b'0'..=b'7' => {
                let mut n = (c - b'0') as u16;
                for _ in 0..2 {
                    if i < bytes.len() - 1 && (b'0'..=b'7').contains(&bytes[i]) {
                        n = n * 8 + (bytes[i] - b'0') as u16;
                        i += 1;
                    } else {
                        break;
                    }
                }
                value.push(u8::try_from(n).map_err(|_| "invalid Git octal")?);
            }
            _ => return Err("unsupported Git path escape".into()),
        }
    }
    Ok(PathBuf::from(OsString::from_vec(value)))
}
fn pattern(path: &str) -> Result<String> {
    if path.contains(['\n', '\r']) {
        return Err("Git cannot exactly exclude newline paths; usage disabled".into());
    }
    let mut output = String::from("/");
    for c in path.chars() {
        if "\\*?[]!# ".contains(c) {
            output.push('\\');
        }
        output.push(c);
    }
    Ok(output)
}
pub fn ensure_excluded(directory: &Path, data: &str, lock: &str) -> Result<()> {
    // Avoid treating broken/unreadable repositories as if they were not repositories.
    let mut repository = false;
    for ancestor in directory.ancestors() {
        match ancestor.join(".git").symlink_metadata() {
            Ok(_) => {
                repository = true;
                break;
            }
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {}
            Err(error) => return Err(error.to_string()),
        }
    }
    if !repository {
        return Ok(());
    }
    let cdup = checked(directory, &["rev-parse", "--show-cdup"])?;
    let cdup = std::str::from_utf8(&cdup)
        .map_err(|_| "invalid Git cdup")?
        .trim_end_matches('\n');
    if !cdup.chars().all(|c| c == '.' || c == '/') {
        return Err("unexpected Git cdup".into());
    }
    let root = directory
        .join(cdup)
        .canonicalize()
        .map_err(|e| e.to_string())?;
    let relative = directory
        .strip_prefix(&root)
        .map_err(|_| "Git root does not contain data directory")?;
    let rel = relative.to_str().ok_or("non-UTF8 Git relative path")?;
    let prefix = if rel.is_empty() {
        String::new()
    } else {
        format!("{rel}/")
    };
    let filenames = [
        format!("{prefix}{data}"),
        format!("{prefix}{lock}"),
        format!("{prefix}.app-usage.tmp-*"),
    ];
    let tracked = checked(
        &root,
        &[
            "ls-files",
            "-z",
            "--",
            if rel.is_empty() { "." } else { rel },
        ],
    )?;
    if tracked.split(|b| *b == 0).any(|p| {
        p == filenames[0].as_bytes()
            || p == filenames[1].as_bytes()
            || p.starts_with(format!("{prefix}.app-usage.tmp-").as_bytes())
    }) {
        return Err(
            "usage data is tracked by Git; refusing updates without touching the index".into(),
        );
    }
    // Only the final temporary suffix is a wildcard; escape all project-path metacharacters.
    let lines = [
        pattern(&filenames[0])?,
        pattern(&filenames[1])?,
        format!("{}*", pattern(&format!("{prefix}.app-usage.tmp-"))?),
    ];
    let exclude = path_output(&checked(
        directory,
        &[
            "rev-parse",
            "--path-format=absolute",
            "--git-path",
            "info/exclude",
        ],
    )?)?;
    if !exclude.is_absolute() || exclude.file_name() != Some(std::ffi::OsStr::new("exclude")) {
        return Err("invalid Git exclude path".into());
    }
    let parent = exclude.parent().ok_or("missing Git info directory")?;
    let dir = fs::Dir::open(parent, true).map_err(|e| e.to_string())?;
    dir.own().map_err(|e| e.to_string())?;
    let _guard = dir
        .lock(".app-usage-exclude.lock")
        .map_err(|e| e.to_string())?;
    let (bytes, stamp) = dir
        .read("exclude", 1024 * 1024, true)
        .map_err(|e| e.to_string())?;
    let mut bytes = bytes.unwrap_or_default();
    let existing =
        std::str::from_utf8(&bytes).map_err(|_| "non-UTF8 Git exclude file; preserving it")?;
    let missing: Vec<_> = lines
        .iter()
        .filter(|line| !existing.lines().any(|s| s == *line))
        .collect();
    if missing.is_empty() {
        return Ok(());
    }
    if !bytes.is_empty() && !bytes.ends_with(b"\n") {
        bytes.push(b'\n');
    }
    for line in missing {
        bytes.extend_from_slice(line.as_bytes());
        bytes.push(b'\n');
    }
    if bytes.len() > 1024 * 1024 {
        return Err("Git exclude file exceeds limit".into());
    }
    dir.publish(
        "exclude",
        &bytes,
        stamp.as_ref(),
        true,
        ".app-usage-exclude.tmp-",
    )
    .map_err(|e| e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn c_quoted_paths_and_exact_patterns() {
        assert_eq!(
            path_output(
                br#""/tmp/a\nb/info/exclude"
"#
            )
            .unwrap(),
            PathBuf::from("/tmp/a\nb/info/exclude")
        );
        assert_eq!(pattern("a [*]!.json").unwrap(), "/a\\ \\[\\*\\]\\!.json");
        assert!(pattern("a\nb").is_err());
    }
}
