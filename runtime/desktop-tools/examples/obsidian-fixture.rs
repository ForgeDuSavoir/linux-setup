//! Private test driver: exercise the production planner/launcher without a real GUI.
use agora_desktop_tools::obsidian;
use std::{ffi::OsString, path::Path};
fn main() {
    let args: Vec<OsString> = std::env::args_os().skip(1).collect();
    let result = if args.first().is_some_and(|v| v == "launch") {
        obsidian::launch(Path::new(&args[1]), &args[2..])
    } else {
        obsidian::arguments(Path::new(""), Path::new(""), &args).map(|v| {
            println!(
                "{}",
                serde_json::to_string(&v.iter().map(|a| a.to_string_lossy()).collect::<Vec<_>>())
                    .unwrap()
            )
        })
    };
    if let Err(e) = result {
        eprintln!("{e}");
        std::process::exit(1);
    }
}
