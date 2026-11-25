//! Settle only the closing address outside the shared metadata lock.
use crate::{
    Result,
    native::{Hyprctl, Native},
    storage::LockedStore,
    workspace::Controller,
};
use std::{
    path::PathBuf,
    process::Command,
    time::{Duration, Instant},
};
fn epoch_guard(epoch: u64) -> String {
    format!("if _G.__workflow_navigation_epoch ~= {epoch} then error(\"stale close event\") end")
}
pub fn run(args: &[String]) -> Result<()> {
    let [ws, address, epoch] = args else {
        return Err("usage: closed-event WS ADDRESS EPOCH".into());
    };
    let ws = ws.parse::<i64>().map_err(|_| "invalid workspace")?;
    let epoch = epoch.parse::<u64>().map_err(|_| "invalid epoch")?;
    if !(1..=crate::state::MAX_ID).contains(&ws)
        || address
            .strip_prefix("0x")
            .is_none_or(|s| s.is_empty() || !s.bytes().all(|b| b.is_ascii_hexdigit()))
    {
        return Err("invalid close event".into());
    }
    let runtime = std::env::var_os("XDG_RUNTIME_DIR")
        .map(PathBuf::from)
        .filter(|p| p.is_absolute())
        .ok_or("absolute runtime required")?
        .join("hyprland");
    let owner = {
        let mut c = Controller {
            native: Hyprctl,
            store: LockedStore::open(&runtime)?,
        };
        c.native.ctl(&["eval", &epoch_guard(epoch)])?;
        let state = c.read_state()?;
        if !state.order.contains(&ws) {
            return Ok(());
        }
        state.owner(ws).to_owned()
    };
    let deadline = Instant::now() + Duration::from_secs(2);
    loop {
        let remaining = deadline.saturating_duration_since(Instant::now());
        if remaining.is_zero() {
            return Ok(());
        }
        let out = crate::process::run(
            Command::new("hyprctl").args(["clients", "-j"]),
            None,
            true,
            Some(remaining),
        )?;
        if !out.status.success() {
            return Err("close settlement query failed; no retry".into());
        }
        let clients: serde_json::Value =
            serde_json::from_slice(&out.stdout).map_err(|_| "invalid clients")?;
        let rows = clients.as_array().ok_or("invalid clients")?;
        // Any unrelated window makes workspace cleanup/navigation unnecessary.
        if rows.iter().any(|c| {
            c["workspace"]["id"].as_i64() == Some(ws)
                && c["address"].as_str() != Some(address.as_str())
        }) {
            return Ok(());
        }
        if rows.iter().any(|c| {
            c["address"].as_str() == Some(address.as_str())
                && c["workspace"]["id"].as_i64() != Some(ws)
        }) {
            return Ok(());
        }
        if !rows
            .iter()
            .any(|c| c["address"].as_str() == Some(address.as_str()))
        {
            break;
        }
        if Instant::now() >= deadline {
            return Ok(());
        }
        std::thread::sleep(Duration::from_millis(25));
    }
    let mut c = Controller {
        native: Hyprctl,
        store: LockedStore::open(&runtime)?,
    };
    c.native.ctl(&["eval", &epoch_guard(epoch)])?;
    let mut state = c.read_state()?;
    if !state.order.contains(&ws) || state.owner(ws) != owner {
        return Ok(());
    }
    let clients = c.native.query("clients")?;
    if clients
        .as_array()
        .ok_or("invalid clients")?
        .iter()
        .any(|c| c["address"].as_str() == Some(address.as_str()))
    {
        return Ok(());
    }
    c.closed_event(&mut state, ws, Some(epoch))
}
