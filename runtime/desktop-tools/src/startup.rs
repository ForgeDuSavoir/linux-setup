//! Per-compositor startup policy. Never a daemon/core/shell reload hook.
use crate::{
    Result,
    core::{Core, REQUEST_TIMEOUT, Sessions},
    desktop::Desktop,
    native::Native,
    state,
    storage::Store,
};
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use std::{
    collections::{BTreeMap, BTreeSet},
    time::{Duration, Instant},
};

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Phase {
    Initializing,
    Failed,
    Ready,
    Deferred,
}
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct Marker {
    pub version: u64,
    pub instance: String,
    pub phase: Phase,
    #[serde(flatten)]
    pub extra: BTreeMap<String, Value>,
}
impl Marker {
    pub fn parse(raw: Value) -> Result<Self> {
        let marker: Self = serde_json::from_value(raw)
            .map_err(|_| "invalid startup marker; inspect before retrying")?;
        if marker.version != 1 {
            return Err("invalid startup marker version".into());
        }
        Ok(marker)
    }
    pub fn new(instance: &str, phase: Phase) -> Self {
        Self {
            version: 1,
            instance: instance.into(),
            phase,
            extra: BTreeMap::new(),
        }
    }
}
pub fn validate_signature(instance: &str) -> Result<()> {
    if instance.is_empty() || instance.chars().count() > 512 {
        Err("missing/invalid Hyprland instance signature".into())
    } else {
        Ok(())
    }
}
/// Pure installer transform: no lock, state read/write, native request or initialization.
pub fn defer_marker(instance: &str, previous: Option<Value>) -> Result<Value> {
    validate_signature(instance)?;
    if let Some(raw) = previous.filter(|v| !v.is_null()) {
        let marker = Marker::parse(raw.clone())?;
        if marker.instance == instance {
            return Ok(json!({"changed":false,"marker":raw}));
        }
    }
    Ok(json!({"changed":true,"marker":Marker::new(instance,Phase::Deferred)}))
}
/// Consume only this compositor's ready, explicitly requested menu.
pub fn claim_menu<S: StartupStore>(store: &mut S, instance: &str) -> Result<bool> {
    validate_signature(instance)?;
    let Some(raw) = store.marker()? else {
        return Ok(false);
    };
    let mut marker = Marker::parse(raw)?;
    if marker.instance != instance || marker.phase != Phase::Ready {
        return Ok(false);
    }
    match marker.extra.get("startup_menu") {
        None => Ok(false), // Older/deferred installations never invent a request.
        Some(Value::String(value)) if value == "consumed" => Ok(false),
        Some(Value::String(value)) if value == "pending" => {
            marker
                .extra
                .insert("startup_menu".into(), json!("consumed"));
            store.write_marker(&marker)?;
            Ok(true)
        }
        _ => Err("invalid startup menu request; inspect marker".into()),
    }
}
pub trait StartupStore: Store {
    fn marker(&mut self) -> Result<Option<Value>>;
    fn write_marker(&mut self, marker: &Marker) -> Result<()>;
    fn backup(&mut self, before: &Value) -> Result<()>;
}
#[derive(Debug)]
pub enum Failure {
    AlreadyAttempted,
    Error(String),
}
impl From<String> for Failure {
    fn from(e: String) -> Self {
        Self::Error(e)
    }
}
/// Wait only on observational readiness, before any ownership reset/core mutation.
/// Wrong instance/ambiguous topology/malformed replies fail closed, never retry resets.
pub fn wait_for_compositor<N: Native>(
    native: &mut N,
    instance: &str,
    budget: Duration,
) -> Result<()> {
    let deadline = Instant::now() + budget;
    loop {
        let mut ready = false;
        let probe = deadline
            .saturating_duration_since(Instant::now())
            .min(Duration::from_secs(2))
            .max(Duration::from_millis(1));
        if let Some(value) = native.startup_query("instances", probe)? {
            let rows = value.as_array().ok_or("invalid compositor instances")?;
            if !rows.is_empty() {
                if rows.len() != 1
                    || rows[0].get("instance").and_then(Value::as_str) != Some(instance)
                {
                    return Err("startup requires exactly this one Hyprland instance".into());
                }
                let probe = deadline
                    .saturating_duration_since(Instant::now())
                    .min(Duration::from_secs(2))
                    .max(Duration::from_millis(1));
                if let Some(value) = native.startup_query("monitors", probe)? {
                    let rows = value.as_array().ok_or("invalid startup monitor snapshot")?;
                    if rows.len() > 1 {
                        return Err(
                            "desktop integration requires one monitor; refusing to change context"
                                .into(),
                        );
                    }
                    if let Some(monitor) = rows.first() {
                        let active = monitor
                            .get("activeWorkspace")
                            .and_then(|w| w.get("id"))
                            .and_then(Value::as_i64)
                            .ok_or("invalid startup monitor active workspace")?;
                        if !(0..=state::MAX_ID).contains(&active) {
                            return Err("invalid startup monitor active workspace".into());
                        }
                        ready = active > 0;
                    }
                }
            }
        }
        if ready {
            return Ok(());
        }
        let remaining = deadline.saturating_duration_since(Instant::now());
        if remaining.is_zero() {
            return Err(
                "Hyprland instance/IPC not ready at graphical startup; no reset performed".into(),
            );
        }
        native.sleep(remaining.min(Duration::from_millis(100)));
    }
}
pub fn wait_for_core<N: Native, S: Store, C: Core>(
    desktop: &mut Desktop<N, S, C>,
    seconds: Duration,
) -> Result<Value> {
    let deadline = Instant::now() + seconds;
    loop {
        match desktop.core.request(&["list"], Duration::from_secs(2)) {
            Ok(value) => return Ok(value),
            Err(error)
                if error == "transport.unavailable"
                    || error.starts_with("child deadline exceeded;") =>
            {
                if Instant::now() >= deadline {
                    return Err("Session Manager unavailable at graphical startup".into());
                }
                desktop.workspace.native.sleep(Duration::from_millis(100));
            }
            Err(error) => return Err(error),
        }
    }
}
pub fn initialize<N: Native, S: StartupStore, C: Core>(
    desktop: &mut Desktop<N, S, C>,
    instance: &str,
) -> std::result::Result<bool, Failure> {
    validate_signature(instance)?;
    if let Some(raw) = desktop.workspace.store.marker()? {
        let marker = Marker::parse(raw)?;
        if marker.instance == instance {
            return match marker.phase {
                Phase::Ready | Phase::Deferred => Ok(false),
                _ => Err(Failure::AlreadyAttempted),
            };
        }
    }
    desktop
        .workspace
        .store
        .write_marker(&Marker::new(instance, Phase::Initializing))?;
    let result = (|| -> Result<()> {
        wait_for_compositor(
            &mut desktop.workspace.native,
            instance,
            Duration::from_secs(10),
        )?;
        let special = desktop.visible_scratchpad()?;
        let clients = desktop.workspace.native.query("clients")?;
        if clients
            .as_array()
            .ok_or("invalid native clients")?
            .iter()
            .any(|c| {
                c["workspace"]["name"]
                    .as_str()
                    .is_some_and(|n| n.starts_with("special:sm-"))
            })
        {
            return Err("scoped scratchpad windows already exist; startup reset refused".into());
        }
        let before = wait_for_core(desktop, Duration::from_secs(10))?;
        let before_ids = Sessions::parse(&before)?;
        let workspaces = desktop.workspace.native.query("workspaces")?;
        let mut existing: BTreeSet<i64> = workspaces
            .as_array()
            .ok_or("invalid native workspaces")?
            .iter()
            .map(|v| v["id"].as_i64().ok_or("invalid workspace ID".to_owned()))
            .collect::<Result<Vec<i64>>>()?
            .into_iter()
            .filter(|id| *id > 0)
            .collect();
        let initial_workspace = desktop.workspace.active()?;
        existing.insert(initial_workspace);
        let state = state::project(None, &existing)?;
        desktop.workspace.store.backup(&before)?;
        desktop.workspace.store.save(&state)?;
        desktop.hide_scratchpad(&special)?;
        for session in before_ids.sessions {
            let reply = desktop
                .core
                .request(&["stop", &session.id.0], REQUEST_TIMEOUT)?;
            if reply.get("stopped_session_id").and_then(Value::as_str)
                != Some(session.id.0.as_str())
            {
                return Err("invalid startup stop acknowledgement".into());
            }
        }
        let remaining = desktop.core.request(&["list"], REQUEST_TIMEOUT)?;
        let remaining = Sessions::parse(&remaining)?;
        if !remaining.sessions.is_empty() || remaining.active_session_id.is_some() {
            return Err("sessions changed during startup; refusing further resets".into());
        }
        if desktop.workspace.active()? != initial_workspace
            || !desktop.visible_scratchpad()?.is_empty()
        {
            return Err("initial empty-session desktop not confirmed".into());
        }
        let mut ready = Marker::new(instance, Phase::Ready);
        ready.extra.insert("startup_menu".into(), json!("pending"));
        desktop.workspace.store.write_marker(&ready)?;
        Ok(())
    })();
    if let Err(error) = result {
        desktop
            .workspace
            .store
            .write_marker(&Marker::new(instance, Phase::Failed))
            .map_err(|write| {
                Failure::Error(format!(
                    "{error}; failed marker could not be persisted: {write}"
                ))
            })?;
        return Err(Failure::Error(error));
    }
    Ok(true)
}
