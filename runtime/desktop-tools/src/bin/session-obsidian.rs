use agora_desktop_tools::{Result, obsidian};
use std::{ffi::OsString, path::PathBuf};
fn run() -> Result<()> {
    let args: Vec<OsString> = std::env::args_os().skip(1).collect();
    if args == ["--version"] {
        println!(
            "session-obsidian {} (Rust; exact registered vault)",
            env!("CARGO_PKG_VERSION")
        );
        return Ok(());
    }
    if args == ["--help"] {
        println!(
            "Usage: session-obsidian [URI/files...]\nNo arguments: confirmed project vault or Agora. --print-uri: resolve without launching."
        );
        return Ok(());
    }
    let print = args == ["--print-uri"];
    let explicit = if print { &[][..] } else { args.as_slice() };
    let home = PathBuf::from(std::env::var_os("HOME").unwrap_or_default());
    let config = std::env::var_os("XDG_CONFIG_HOME")
        .filter(|v| !v.is_empty())
        .map(PathBuf::from)
        .unwrap_or(home.join(".config"));
    let plan = obsidian::arguments(&home, &config, explicit)?;
    if print {
        println!("{}", plan[0].to_str().ok_or("non-UTF8 URI")?);
        return Ok(());
    }
    // Never PATH-resolve 'obsidian': CLI registration can shadow the graphical launcher.
    obsidian::launch(std::path::Path::new("/usr/bin/obsidian"), &plan)
}
fn main() {
    if let Err(e) = run() {
        eprintln!("Session Obsidian: {e}");
        std::process::exit(1);
    }
}
