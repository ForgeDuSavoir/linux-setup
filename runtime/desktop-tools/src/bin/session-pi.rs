use agora_desktop_tools::{Result, pi};
use std::path::PathBuf;
fn run() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args == ["--version"] {
        println!(
            "session-pi {} (Rust; captured launch origin)",
            env!("CARGO_PKG_VERSION")
        );
        return Ok(());
    }
    let explicit = match args.as_slice() {
        [] => false,
        [arg] if arg == "--agora" => true,
        _ => return Err("usage: session-pi [--agora]".into()),
    };
    let home = PathBuf::from(std::env::var_os("HOME").ok_or("HOME is required")?);
    let config = std::env::var_os("XDG_CONFIG_HOME")
        .filter(|s| !s.is_empty())
        .map(PathBuf::from)
        .unwrap_or(home.join(".config"));
    let plan = pi::plan(&home, &config, explicit)?;
    let context = pi::capture(&home, plan.expected.as_deref());
    pi::launch(&home, &plan, &context)
}
fn main() {
    if let Err(e) = run() {
        eprintln!("Session Pi launcher: {e}");
        std::process::exit(1);
    }
}
