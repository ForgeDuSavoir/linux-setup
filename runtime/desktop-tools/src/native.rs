//! Direct hyprctl argv. Preserve the reference's unbounded native waits in R1.
use crate::Result;
use serde_json::Value;
use std::{process::Command, time::Duration};

pub trait Native {
    fn ctl(&mut self, args: &[&str]) -> Result<String>;
    fn query(&mut self, name: &str) -> Result<Value> {
        serde_json::from_str(&self.ctl(&[name, "-j"])?)
            .map_err(|e| format!("invalid native JSON: {e}"))
    }
    fn sleep(&mut self, duration: Duration) {
        std::thread::sleep(duration);
    }
}
pub struct Hyprctl;
impl Native for Hyprctl {
    fn ctl(&mut self, args: &[&str]) -> Result<String> {
        let output = Command::new("hyprctl")
            .args(args)
            .output()
            .map_err(|e| e.to_string())?;
        let stdout =
            String::from_utf8(output.stdout).map_err(|_| "invalid native stdout encoding")?;
        let stderr =
            String::from_utf8(output.stderr).map_err(|_| "invalid native stderr encoding")?;
        if !output.status.success()
            || [&stdout, &stderr]
                .iter()
                .any(|s| s.trim_start().to_ascii_lowercase().starts_with("error"))
        {
            return Err(format!(
                "native request failed; result may be uncertain; no retry: {stdout} {stderr}"
            ));
        }
        Ok(stdout)
    }
}
pub fn focus(ws: i64, fresh: bool) -> String {
    let dispatch = format!("hl.dispatch(hl.dsp.focus({{ workspace = {ws} }}))");
    if fresh {
        format!(
            "if hl.get_workspace({ws}) then error(\"workspace target already exists\") end; {dispatch}"
        )
    } else {
        format!("hl.dsp.focus({{ workspace = {ws} }})")
    }
}
/// Read-only compositor acknowledgement, after focus and metadata finalization.
/// No polling/sleep, and no second focus if another navigation has won.
pub fn confirm_empty(ws: i64) -> String {
    format!(
        "local w=hl.get_active_workspace(); if not hl.get_workspace({ws}) or not w or w.id ~= {ws} or #hl.get_workspace_windows({ws}) ~= 0 then error(\"new empty workspace is not active\") end"
    )
}
pub fn move_window(ws: i64, address: &str, fresh: bool) -> Result<String> {
    if address.is_empty() || !address.bytes().all(|c| c.is_ascii_hexdigit() || c == b'x') {
        return Err("unsafe window address".into());
    }
    let dispatch =
        format!("hl.dsp.window.move({{ workspace = {ws}, window = \"address:{address}\" }})");
    Ok(if fresh {
        format!(
            "if hl.get_workspace({ws}) then error(\"workspace target already exists\") end; hl.dispatch({dispatch})"
        )
    } else {
        dispatch
    })
}
