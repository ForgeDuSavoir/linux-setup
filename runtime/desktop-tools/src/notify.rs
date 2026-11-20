//! Capture once / send literally through the existing standard notification client.
use crate::{Result, process};
use serde_json::Value;
use std::{path::Path, process::Command, time::Duration};

#[derive(Clone, Debug, PartialEq)]
pub enum Context {
    Global,
    Unowned,
    Session(String),
}
impl Context {
    pub fn parse(value: &str) -> Result<Self> {
        match value {
            "global" => Ok(Self::Global),
            "neutral" => Ok(Self::Unowned),
            _ => {
                let id = value
                    .strip_prefix("session:")
                    .ok_or("context must be global, neutral or session:<canonical UUID>")?;
                if id.len() != 36
                    || !id.bytes().enumerate().all(|(i, b)| {
                        if [8, 13, 18, 23].contains(&i) {
                            b == b'-'
                        } else {
                            b.is_ascii_digit() || (b'a'..=b'f').contains(&b)
                        }
                    })
                {
                    return Err("invalid canonical notification UUID".into());
                }
                Ok(Self::Session(id.into()))
            }
        }
    }
    pub fn label(&self) -> String {
        match self {
            Self::Global => "global".into(),
            Self::Unowned => "neutral".into(),
            Self::Session(id) => format!("session:{id}"),
        }
    }
}
#[derive(Clone, Debug, PartialEq)]
pub struct Send {
    pub context: Option<String>,
    pub global: bool,
    pub urgency: String,
    pub app: String,
    pub expiration: Option<String>,
    pub replace: Option<String>,
    pub summary: String,
    pub body: String,
}
#[derive(Clone, Debug, PartialEq)]
pub enum Action {
    Capture,
    Send(Send),
    Help,
    Version,
}
fn syntax(message: &str) -> String {
    format!("usage: agora-notify capture|send [options] SUMMARY [BODY]: {message}")
}
fn integer(raw: &str) -> Option<String> {
    let raw = raw.trim();
    let (negative, digits) = if let Some(s) = raw.strip_prefix('-') {
        (true, s)
    } else {
        (false, raw.strip_prefix('+').unwrap_or(raw))
    };
    if digits.is_empty()
        || digits.starts_with('_')
        || digits.ends_with('_')
        || digits.contains("__")
        || !digits.bytes().all(|b| b.is_ascii_digit() || b == b'_')
    {
        return None;
    }
    let digits = digits.replace('_', "");
    let canonical = digits.trim_start_matches('0');
    Some(if canonical.is_empty() {
        "0".into()
    } else {
        format!("{}{canonical}", if negative { "-" } else { "" })
    })
}
fn negative_number(raw: &str) -> bool {
    raw.strip_prefix('-').is_some_and(|v| {
        if let Some((whole, fraction)) = v.split_once('.') {
            !fraction.is_empty()
                && whole.bytes().all(|b| b.is_ascii_digit())
                && fraction.bytes().all(|b| b.is_ascii_digit())
        } else {
            !v.is_empty() && v.bytes().all(|b| b.is_ascii_digit())
        }
    })
}
pub fn parse(args: &[String]) -> Result<Action> {
    if args == ["--version"] {
        return Ok(Action::Version);
    }
    if args == ["--help"] || args == ["-h"] {
        return Ok(Action::Help);
    }
    if args.first().is_some_and(|s| s == "capture") {
        return match &args[1..] {
            [] => Ok(Action::Capture),
            [s] if s == "--help" || s == "-h" => Ok(Action::Help),
            _ => Err(syntax("capture takes no options/arguments")),
        };
    }
    if args.first().is_none_or(|s| s != "send") {
        return Err(syntax("missing/unknown command"));
    }
    let mut send = Send {
        context: None,
        global: false,
        urgency: "normal".into(),
        app: "Agora scripts".into(),
        expiration: None,
        replace: None,
        summary: String::new(),
        body: String::new(),
    };
    let mut positional = Vec::new();
    let mut i = 1;
    let mut options = true;
    while i < args.len() {
        let arg = &args[i];
        i += 1;
        if options && (arg == "--help" || arg == "-h") {
            return Ok(Action::Help);
        }
        if options && arg == "--" {
            options = false;
            continue;
        }
        if options && arg != "-" && arg.starts_with('-') && !negative_number(arg) {
            let (option, attached) = if arg.starts_with("--") {
                let (prefix, value) = arg
                    .split_once('=')
                    .map(|(a, b)| (a, Some(b.to_owned())))
                    .unwrap_or((arg, None));
                let matches: Vec<_> = [
                    "--context",
                    "--global",
                    "--urgency",
                    "--app-name",
                    "--expire-time",
                    "--replace-id",
                    "--help",
                ]
                .into_iter()
                .filter(|name| name.starts_with(prefix))
                .collect();
                if matches.len() != 1 {
                    return Err(syntax("unknown or ambiguous option"));
                }
                (matches[0], value)
            } else {
                let key = arg.get(..2).ok_or_else(|| syntax("invalid option"))?;
                let option = match key {
                    "-u" => "--urgency",
                    "-a" => "--app-name",
                    "-t" => "--expire-time",
                    "-r" => "--replace-id",
                    _ => return Err(syntax("unknown option")),
                };
                (
                    option,
                    if arg.len() > 2 {
                        Some(arg[2..].to_owned())
                    } else {
                        None
                    },
                )
            };
            if option == "--help" {
                return if attached.is_none() {
                    Ok(Action::Help)
                } else {
                    Err(syntax("help takes no value"))
                };
            }
            if option == "--global" {
                if attached.is_some() || send.context.is_some() {
                    return Err(syntax("conflicting context options"));
                }
                send.global = true;
                continue;
            }
            let value = if let Some(v) = attached {
                v
            } else {
                let value = args.get(i).ok_or_else(|| syntax("missing option value"))?;
                if value != "-" && value.starts_with('-') && !negative_number(value) {
                    return Err(syntax("missing option value"));
                }
                i += 1;
                value.clone()
            };
            match option {
                "--context" => {
                    if send.global {
                        return Err(syntax("conflicting context options"));
                    }
                    send.context = Some(value);
                }
                "--urgency" => {
                    if !["low", "normal", "critical"].contains(&value.as_str()) {
                        return Err(syntax("invalid urgency"));
                    }
                    send.urgency = value;
                }
                "--app-name" => send.app = value,
                "--expire-time" => {
                    send.expiration =
                        Some(integer(&value).ok_or_else(|| syntax("invalid integer"))?)
                }
                "--replace-id" => {
                    send.replace = Some(integer(&value).ok_or_else(|| syntax("invalid integer"))?)
                }
                _ => unreachable!(),
            }
        } else {
            positional.push(arg.clone());
        }
    }
    if positional.is_empty() || positional.len() > 2 {
        return Err(syntax("expected summary and optional body"));
    }
    send.summary = positional.remove(0);
    send.body = positional.pop().unwrap_or_default();
    Ok(Action::Send(send))
}
pub fn confirmed_context(state: &Value) -> Result<Context> {
    if !state.is_object() || state.get("context_confirmed").and_then(Value::as_bool) != Some(true) {
        return Err("desktop context is not confirmed; choose explicit context or global".into());
    }
    let displayed = state
        .get("displayed_context")
        .and_then(Value::as_str)
        .ok_or("invalid displayed context")?;
    if displayed == "neutral" && state.get("active_session_id").is_none_or(Value::is_null) {
        return Ok(Context::Unowned);
    }
    if state.get("active_session_id").and_then(Value::as_str) != Some(displayed)
        || !state
            .get("sessions")
            .and_then(Value::as_array)
            .is_some_and(|rows| {
                rows.iter()
                    .any(|row| row.get("id").and_then(Value::as_str) == Some(displayed))
            })
    {
        return Err("inconsistent session context".into());
    }
    Context::parse(&format!("session:{displayed}"))
}
pub fn capture(home: &Path, inherited: Option<&str>) -> Result<Context> {
    if let Some(value) = inherited {
        return Context::parse(value);
    }
    let output = process::run(
        Command::new(home.join(".local/bin/session-desktop")).arg("status"),
        None,
        true,
        Some(Duration::from_secs(35)),
    )?;
    if !output.status.success() {
        return Err("desktop status unavailable".into());
    }
    let state =
        serde_json::from_slice(&output.stdout).map_err(|_| "invalid desktop status response")?;
    confirmed_context(&state)
}
impl Send {
    pub fn arguments(&self, inherited: Option<&str>) -> Result<Vec<String>> {
        let context = Context::parse(if self.global {
            "global"
        } else {
            self.context.as_deref().or(inherited).unwrap_or("global")
        })?;
        let mut args = vec![
            "--hint".into(),
            format!("string:x-agora-context:{}", context.label()),
            "--app-name".into(),
            self.app.clone(),
            "--urgency".into(),
            self.urgency.clone(),
        ];
        if let Some(value) = &self.expiration {
            args.extend(["--expire-time".into(), value.clone()]);
        }
        if let Some(value) = &self.replace {
            value
                .parse::<u32>()
                .map_err(|_| "replacement ID must be an unsigned 32-bit integer")?;
            args.extend(["--replace-id".into(), value.clone()]);
        }
        args.extend(["--".into(), self.summary.clone(), self.body.clone()]);
        Ok(args)
    }
    pub fn send(&self, inherited: Option<&str>) -> Result<()> {
        let args = self.arguments(inherited)?;
        let output = process::run(
            Command::new("notify-send").args(args),
            None,
            true,
            Some(Duration::from_secs(10)),
        )?;
        if !output.status.success() {
            return Err("notification emission failed; outcome may be uncertain; no retry".into());
        }
        Ok(())
    }
}
