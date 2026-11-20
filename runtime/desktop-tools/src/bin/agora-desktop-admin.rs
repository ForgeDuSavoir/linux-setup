use agora_desktop_tools::{Result, admin};
use std::io::Read;
fn run() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args == ["--version"] {
        println!(
            "agora-desktop-admin {} (admin protocol 1)",
            env!("CARGO_PKG_VERSION")
        );
        return Ok(());
    }
    let [op] = args.as_slice() else {
        return Err(
            "usage: agora-desktop-admin capabilities|project-state|validate-state|defer-marker"
                .into(),
        );
    };
    let input = if op == "capabilities" {
        serde_json::Value::Null
    } else {
        let mut bytes = Vec::new();
        std::io::stdin()
            .take(4 * 1024 * 1024 + 1)
            .read_to_end(&mut bytes)
            .map_err(|e| e.to_string())?;
        if bytes.len() > 4 * 1024 * 1024 {
            return Err("admin input exceeds 4 MiB".into());
        }
        serde_json::from_slice(&bytes).map_err(|e| format!("invalid admin JSON: {e}"))?
    };
    println!("{}", admin::run(op, input)?);
    Ok(())
}
fn main() {
    if let Err(e) = run() {
        eprintln!("agora-desktop-admin: {e}");
        std::process::exit(1);
    }
}
