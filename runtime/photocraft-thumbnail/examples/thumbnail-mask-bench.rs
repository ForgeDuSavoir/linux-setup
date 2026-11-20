//! Synthetic benchmark driver only; never installed. Caller supplies private fixtures.
use photocraft_thumbnail::{Result, apply_mask};
fn main() -> Result<()> {
    let args: Vec<_> = std::env::args_os().skip(1).collect();
    if args.len() != 3 {
        return Err("private TEMPLATE SOURCE OUTPUT paths required".into());
    }
    let mut samples = Vec::new();
    for _ in 0..31 {
        let now = std::time::Instant::now();
        apply_mask(
            args[0].as_ref(),
            args[1].as_ref(),
            args[2].as_ref(),
            "top",
            "bottom",
        )?;
        std::fs::remove_file(&args[2])?;
        samples.push(now.elapsed().as_secs_f64() * 1000.);
    }
    println!("{}", serde_json::to_string(&samples)?);
    Ok(())
}
