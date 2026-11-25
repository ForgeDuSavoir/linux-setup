//! Direct hyprctl argv. Ordinary calls retain R1 waits; startup-only readonly
//! readiness probes use a separate bounded transport.
use crate::Result;
use serde_json::Value;
use std::{process::Command, time::Duration};

pub trait Native {
    fn ctl(&mut self, args: &[&str]) -> Result<String>;
    fn query(&mut self, name: &str) -> Result<Value> {
        serde_json::from_str(&self.ctl(&[name, "-j"])?)
            .map_err(|e| format!("invalid native JSON: {e}"))
    }
    /// Startup-only readonly probes. None means a recognized not-ready response.
    fn startup_query(&mut self, name: &str, _timeout: Duration) -> Result<Option<Value>> {
        self.query(name).map(Some)
    }
    fn sleep(&mut self, duration: Duration) {
        std::thread::sleep(duration);
    }
}
pub struct Hyprctl;
/// Narrow startup response classification: never normalize malformed JSON globally.
pub(crate) fn startup_reply(name: &str, success: bool, stdout: &[u8]) -> Result<Option<Value>> {
    let text = std::str::from_utf8(stdout)
        .map_err(|_| format!("startup hyprctl {name}: invalid UTF-8"))?;
    if !success {
        if name == "monitors"
            && text.trim_start().starts_with("Couldn't connect to ")
            && text.contains("/.socket.sock")
        {
            return Ok(None);
        }
        return Err(format!(
            "startup hyprctl {name} failed; refusing non-readiness retry"
        ));
    }
    // Hyprctl 0.56.2 emits "\n]\n\n" (exit 0) for no complete instance lock.
    if name == "instances" && text.trim() == "]" {
        return Ok(None);
    }
    serde_json::from_str(text)
        .map(Some)
        .map_err(|e| format!("startup hyprctl {name}: invalid JSON: {e}"))
}
impl Native for Hyprctl {
    fn startup_query(&mut self, name: &str, timeout: Duration) -> Result<Option<Value>> {
        if !["instances", "monitors"].contains(&name) {
            return Err("only readonly startup probes are allowed".into());
        }
        let result = crate::process::run(
            Command::new("hyprctl").args([name, "-j"]),
            None,
            true,
            Some(timeout),
        );
        match result {
            Ok(output) => startup_reply(name, output.status.success(), &output.stdout),
            Err(e) if e.starts_with("child deadline exceeded;") => Ok(None),
            Err(e) => Err(format!("startup hyprctl {name}: {e}")),
        }
    }
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
/// Session transitions only: style is read synchronously at animation start.
pub fn session_focus(ws: i64, fresh: bool) -> String {
    let body = if fresh {
        focus(ws, true)
    } else {
        format!("hl.dispatch({})", focus(ws, false))
    };
    format!(
        "local base = _G.__workflow_workspace_animation or {{leaf=\"workspaces\",enabled=true,speed=5,bezier=\"wind\",style=\"slidevert\"}}; local ok, why = pcall(function() hl.animation({{leaf=base.leaf,enabled=base.enabled,speed=base.speed,bezier=base.bezier,style=\"slidefade\"}}); {body} end); hl.animation(base); if not ok then error(why) end"
    )
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
