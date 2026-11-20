use agora_desktop_tools::{Result, files};
use std::path::PathBuf;
fn run() -> Result<()> {
    let args: Vec<_> = std::env::args_os().skip(1).collect();
    if args == ["--version"] {
        println!(
            "session-files {} (Rust; project-or-home)",
            env!("CARGO_PKG_VERSION")
        );
        return Ok(());
    }
    if args == ["--help"] || args == ["-h"] {
        println!(
            "Usage: session-files\nOpen the confirmed session project or HOME with the default file manager."
        );
        return Ok(());
    }
    if !args.is_empty() {
        return Err("usage: session-files (SUPER+E only; no path arguments)".into());
    }
    let home = PathBuf::from(std::env::var_os("HOME").ok_or("HOME is required")?);
    let path = files::destination(&home)?;
    files::launch(&path)
}
fn main() {
    if let Err(e) = run() {
        eprintln!("Session files: {e}");
        std::process::exit(1);
    }
}
