//! Private test driver for the production readonly gate; never resets sessions.
use agora_desktop_tools::{native::Hyprctl, startup};
use std::time::Duration;
fn main() {
    let args: Vec<_> = std::env::args().skip(1).collect();
    assert_eq!(args.len(), 2);
    let budget = args[1].parse::<u64>().unwrap();
    if let Err(e) =
        startup::wait_for_compositor(&mut Hyprctl, &args[0], Duration::from_millis(budget))
    {
        eprintln!("{e}");
        std::process::exit(1);
    }
    println!("ready");
}
