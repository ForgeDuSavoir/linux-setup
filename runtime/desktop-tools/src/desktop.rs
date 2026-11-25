//! Graphical adapter policy, reusing the R1 controller and its already-owned lock.
use crate::{
    Result,
    core::{Core, REQUEST_TIMEOUT, SessionId, Sessions, Source, acknowledged_session},
    native::Native,
    state::State,
    storage::Store,
    workspace::Controller,
};
use serde_json::{Value, json};
const SLOTS: [&str; 5] = ["ai", "notes", "tasks", "4", "5"];

/// A real Neutral UUID is Session, never the legacy Unowned sentinel.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum Owner {
    Unowned,
    Session(SessionId),
    Unknown,
}
impl Owner {
    pub fn parse(label: &str) -> Result<Self> {
        match label {
            "neutral" => Ok(Self::Unowned),
            "unknown" => Ok(Self::Unknown),
            _ => Ok(Self::Session(SessionId::try_from(label.to_owned())?)),
        }
    }
    pub fn active(id: Option<&SessionId>) -> Self {
        id.cloned().map(Self::Session).unwrap_or(Self::Unowned)
    }
    pub fn label(&self) -> &str {
        match self {
            Self::Unowned => "neutral",
            Self::Unknown => "unknown",
            Self::Session(id) => &id.0,
        }
    }
    pub fn known(&self, list: &Sessions) -> bool {
        match self {
            Self::Unowned => true,
            Self::Unknown => false,
            Self::Session(id) => list.contains(id),
        }
    }
}

#[derive(Clone, Debug)]
pub enum Action {
    Start(Source),
    Switch(SessionId),
    Deactivate,
    Stop(SessionId),
    Status,
    Close(Option<i64>),
}
impl Action {
    pub fn parse(args: &[String]) -> Result<Self> {
        match args {
            [a] if a=="status"=>Ok(Self::Status),[a] if a=="deactivate"=>Ok(Self::Deactivate),[a] if a=="close"=>Ok(Self::Close(None)),
            [a,b] if a=="start"&&b=="--neutral"=>Ok(Self::Start(Source::Neutral {})),
            [a,b,name] if a=="start"&&b=="--project"&&!name.is_empty()=>Ok(Self::Start(Source::Project{project_name:name.clone()})),
            [a,id] if a=="switch"=>Ok(Self::Switch(SessionId::try_from(id.clone())?)),
            [a,id] if a=="stop"=>Ok(Self::Stop(SessionId::try_from(id.clone())?)),
            [a,id] if a=="close"&&!id.is_empty()&&id.bytes().all(|b|b.is_ascii_digit())=>Ok(Self::Close(Some(id.parse().map_err(|_|"workspace ID out of range")?))),
            _=>Err("usage: session-desktop start --neutral|start --project NAME|switch UUID|deactivate|close [WORKSPACE_ID]|stop UUID".into())
        }
    }
}
fn rows(value: Value) -> Result<Vec<Value>> {
    value
        .as_array()
        .cloned()
        .ok_or("invalid native array".into())
}
fn special_name(value: &Value) -> &str {
    value
        .get("specialWorkspace")
        .and_then(|v| v.get("name"))
        .and_then(Value::as_str)
        .unwrap_or("")
}
fn safe_special(name: &str) -> bool {
    name.strip_prefix("special:").is_some_and(|s| {
        !s.is_empty()
            && s.len() <= 100
            && s.bytes()
                .all(|b| b.is_ascii_alphanumeric() || b == b'_' || b == b'-')
    })
}

pub struct Desktop<N: Native, S: Store, C: Core> {
    pub workspace: Controller<N, S>,
    pub core: C,
}
impl<N: Native, S: Store, C: Core> Desktop<N, S, C> {
    fn request(&mut self, args: &[&str]) -> Result<Value> {
        self.core.request(args, REQUEST_TIMEOUT)
    }
    pub fn visible_scratchpad(&mut self) -> Result<String> {
        let monitors = rows(self.workspace.native.query("monitors")?)?;
        if monitors.len() != 1 {
            return Err(
                "desktop integration requires one monitor; refusing to change context".into(),
            );
        }
        Ok(special_name(&monitors[0]).into())
    }
    pub(crate) fn hide_scratchpad(&mut self, name: &str) -> Result<()> {
        if name.is_empty() {
            return Ok(());
        }
        if !safe_special(name) {
            return Err("unsafe special workspace name; refusing to change context".into());
        }
        self.workspace.native.ctl(&[
            "dispatch",
            &format!("hl.dsp.workspace.toggle_special(\"{}\")", &name[8..]),
        ])?;
        if !self.visible_scratchpad()?.is_empty() {
            return Err("scratchpad did not hide; refusing to change context".into());
        }
        Ok(())
    }
    pub fn pick_workspace(&mut self, state: &mut State, owner: &str) -> Result<(i64, bool)> {
        let owned: Vec<_> = state
            .order
            .iter()
            .copied()
            .filter(|ws| state.owner(*ws) == owner)
            .collect();
        if let Some(first) = owned.first() {
            let preferred = state.preferred.get(owner).filter(|ws| owned.contains(ws));
            Ok((preferred.copied().unwrap_or(*first), false))
        } else {
            Ok((self.workspace.fresh_workspace(state, owner, None)?, true))
        }
    }
    fn guard_stop(&mut self, state: &State, id: &SessionId) -> Result<()> {
        if self.session_empty(state, id)? {
            Ok(())
        } else {
            Err("session has open windows; stop refused".into())
        }
    }
    fn session_empty(&mut self, state: &State, id: &SessionId) -> Result<bool> {
        let owned: Vec<_> = state
            .order
            .iter()
            .copied()
            .filter(|ws| state.owner(*ws) == id.0)
            .collect();
        let specials: Vec<_> = SLOTS
            .iter()
            .map(|slot| format!("special:sm-{}-{slot}", id.0))
            .collect();
        for client in rows(self.workspace.native.query("clients")?)? {
            let ws = &client["workspace"];
            if ws
                .get("name")
                .and_then(Value::as_str)
                .is_some_and(|s| specials.iter().any(|v| v == s))
                || ws
                    .get("id")
                    .and_then(Value::as_i64)
                    .is_some_and(|id| id > 0 && owned.contains(&id))
            {
                return Ok(false);
            }
        }
        Ok(true)
    }
    pub fn stop_fallback(before: &Sessions, id: &SessionId) -> Result<Option<SessionId>> {
        let index = before
            .sessions
            .iter()
            .position(|s| &s.id == id)
            .ok_or("not_found.session")?;
        if before.sessions.len() == 1 {
            return Err("cannot stop the last open session; open another session first".into());
        }
        Ok(if before.active_session_id.as_ref() == Some(id) {
            Some(
                before.sessions[(index + 1) % before.sessions.len()]
                    .id
                    .clone(),
            )
        } else {
            None
        })
    }
    fn stop_session(
        &mut self,
        state: &mut State,
        id: &SessionId,
        fallback: Option<SessionId>,
    ) -> Result<Value> {
        if fallback.is_none() && state.owner(self.workspace.active()?) == id.0 {
            return Err(
                "displayed and logical sessions differ; select the active session before stopping"
                    .into(),
            );
        }
        self.guard_stop(state, id)?;
        if let Some(target_id) = &fallback {
            let switched = self.request(&["switch", &target_id.0])?;
            if acknowledged_session(&switched)? != *target_id {
                return Err(
                    "invalid switch acknowledgement; original session was not stopped".into(),
                );
            }
            let (target, fresh) = self.pick_workspace(state, &target_id.0)?;
            self.workspace.select_session(state, target, fresh, false)?;
            if self.workspace.active()? != target || !self.visible_scratchpad()?.is_empty() {
                return Err(
                    "fallback desktop not confirmed; original session was not stopped".into(),
                );
            }
            let live = Sessions::parse(&self.request(&["list"])?)?;
            if live.active_session_id.as_ref() != Some(target_id)
                || !live.contains(target_id)
                || !live.contains(id)
            {
                return Err(
                    "sessions changed during fallback; original session was not stopped".into(),
                );
            }
            self.guard_stop(state, id)?;
        }
        let reply = self.request(&["stop", &id.0])?;
        if reply.get("stopped_session_id").and_then(Value::as_str) != Some(&id.0) {
            return Err("invalid stop acknowledgement".into());
        }
        if let Some(target_id) = fallback {
            let after = Sessions::parse(&self.request(&["list"])?)?;
            if after.active_session_id.as_ref() != Some(&target_id) || after.contains(id) {
                return Err(
                    "stop outcome/selection changed concurrently; inspect session state".into(),
                );
            }
        }
        self.forget_session(state, id)?;
        Ok(reply)
    }
    fn forget_session(&mut self, state: &mut State, id: &SessionId) -> Result<()> {
        state.owners.retain(|_, owner| *owner != id.0);
        state
            .order
            .retain(|ws| state.owners.contains_key(&ws.to_string()));
        state.preferred.remove(&id.0);
        self.workspace.cleanup(state)
    }
    fn close_current(
        &mut self,
        state: &mut State,
        before: &Sessions,
        before_raw: &Value,
        special: &str,
        expected: Option<i64>,
    ) -> Result<Value> {
        let current = self.workspace.active()?;
        let context = Owner::parse(state.owner(current))?;
        let owner = context.label().to_owned();
        if current <= 0
            || expected.is_some_and(|id| id != current)
            || context != Owner::active(before.active_session_id.as_ref())
        {
            return Err("displayed and logical sessions differ; close refused".into());
        }
        let allowed = special == "special:global"
            || SLOTS.iter().any(|slot| {
                special == format!("special:sm-{owner}-{slot}")
                    || (owner == "neutral" && special == format!("special:session-{slot}"))
            });
        if !special.is_empty() && !allowed {
            return Err("scratchpad and displayed session differ; close refused".into());
        }
        let client = self.workspace.native.query("activewindow")?;
        let target = if special.is_empty() {
            client["workspace"]["id"].as_i64() == Some(current)
        } else {
            client["workspace"]["name"].as_str() == Some(special)
        };
        let address = client.get("address").and_then(Value::as_str).unwrap_or("");
        if target
            && address
                .strip_prefix("0x")
                .is_some_and(|a| !a.is_empty() && a.bytes().all(|b| b.is_ascii_hexdigit()))
        {
            let name = serde_json::to_string(special).map_err(|e| e.to_string())?;
            let code = format!(
                r#"
local ws = hl.get_active_workspace()
local sp = hl.get_active_special_workspace()
local w = hl.get_active_window()
if not ws or ws.id ~= {current} or (sp and sp.name or "") ~= {name}
    or not w or w.address ~= "{address}"
    or not w.mapped or not w.visible or not w.workspace
    or ({name} ~= "" and w.workspace.name ~= {name})
    or ({name} == "" and w.workspace.id ~= {current}) then
    error("visible close target changed; close refused")
end
hl.dispatch(hl.dsp.window.close({{ window = "address:{address}" }}))
"#
            );
            self.workspace.native.ctl(&["eval", &code])?;
            return Ok(json!({"closed_window_requested":true}));
        }
        if !special.is_empty() {
            return Err("no confirmed visible scratchpad window; close refused".into());
        }
        if owner == "neutral" {
            return Ok(json!({"noop":true}));
        }
        let id = SessionId::try_from(owner)?;
        let fallback = Self::stop_fallback(before, &id)?;
        self.guard_stop(state, &id)?;
        let live = self.request(&["list"])?;
        Sessions::parse(&live)?;
        if live != *before_raw
            || self.workspace.active()? != current
            || !self.visible_scratchpad()?.is_empty()
        {
            return Err("context changed before empty-session close; close refused".into());
        }
        self.stop_session(state, &id, fallback)
    }
    pub fn status(&mut self) -> Result<Value> {
        let state = self
            .workspace
            .store
            .read()?
            .unwrap_or(json!({"version":3,"owners":{}}));
        let version = state
            .get("version")
            .and_then(Value::as_u64)
            .filter(|v| [2, 3].contains(v))
            .ok_or("unsupported workspace state")?;
        let owners = state
            .get("owners")
            .and_then(Value::as_object)
            .ok_or("invalid workspace owners")?;
        let monitors = rows(self.workspace.native.query("monitors")?)?;
        let monitor = monitors
            .iter()
            .find(|m| m.get("focused").and_then(Value::as_bool) == Some(true))
            .or_else(|| {
                if monitors.len() == 1 {
                    monitors.first()
                } else {
                    None
                }
            });
        let mut owner = "unknown".to_owned();
        if let Some(monitor) = monitor {
            let ws = monitor["activeWorkspace"]["id"].as_i64().unwrap_or(0);
            if ws > 0 {
                let key = if version == 3 { ws } else { ws / 2 + ws % 2 };
                owner = owners
                    .get(&key.to_string())
                    .map(|v| v.as_str().ok_or("invalid workspace owner"))
                    .transpose()?
                    .unwrap_or("neutral")
                    .into();
            }
            let special = special_name(monitor);
            let mismatched = special
                .strip_prefix("special:sm-")
                .and_then(|s| s.rsplit_once('-'))
                .is_some_and(|(id, slot)| {
                    id.len() == 36
                        && id
                            .bytes()
                            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b) || b == b'-')
                        && SLOTS.contains(&slot)
                        && id != owner
                });
            if mismatched || (special.starts_with("special:session-") && owner != "neutral") {
                owner = "unknown".into();
            }
        }
        let mut result = self.request(&["list"])?;
        let list = Sessions::parse(&result)?;
        let context = Owner::parse(&owner)?;
        let known = context.known(&list);
        result["displayed_context"] = json!(if known { owner.as_str() } else { "unknown" });
        result["context_confirmed"] = json!(
            known
                && owner
                    == list
                        .active_session_id
                        .as_ref()
                        .map(|id| id.0.as_str())
                        .unwrap_or("neutral")
        );
        Ok(result)
    }
    /// CLI owns one LockedStore; no native mutation or file replacement by status.
    pub fn invoke(&mut self, action: Action) -> Result<Value> {
        if matches!(action, Action::Status) {
            return self.status();
        }
        if let Action::Start(source) = &action {
            source.arguments()?;
        }
        let special = self.visible_scratchpad()?;
        let before_raw = self.request(&["list"])?;
        let before = Sessions::parse(&before_raw)?;
        let fallback = if let Action::Stop(id) = &action {
            Self::stop_fallback(&before, id)?
        } else {
            None
        };
        let mut state = if matches!(action, Action::Close(_)) {
            self.workspace.read_state()?
        } else {
            self.workspace.load()?
        };
        if let Action::Close(expected) = action {
            return self.close_current(&mut state, &before, &before_raw, &special, expected);
        }
        let original_ownership = state.clone();
        if !matches!(action, Action::Stop(_)) {
            self.workspace.cleanup(&mut state)?;
        }
        let current = self.workspace.active()?;
        if current > 0 {
            state.preferred.insert(state.owner(current).into(), current);
        }
        let previous = if matches!(action, Action::Start(_)) {
            before
                .active_session_id
                .clone()
                .filter(|id| current > 0 && state.owner(current) == id.0)
        } else {
            None
        };
        self.hide_scratchpad(&special)?;
        if let Action::Stop(id) = &action {
            return self.stop_session(&mut state, id, fallback);
        }
        let (reply, owner) = match action {
            Action::Start(source) => {
                let args = source.arguments()?;
                let mut argv = vec!["start"];
                argv.extend(args.iter().map(String::as_str));
                let reply = self.request(&argv)?;
                let id = acknowledged_session(&reply)?;
                (reply, id.0)
            }
            Action::Switch(id) => {
                if !before.contains(&id) {
                    return Err("not_found.session".into());
                }
                let reply = self.request(&["switch", &id.0])?;
                (reply, id.0)
            }
            Action::Deactivate => (self.request(&["deactivate"])?, "neutral".into()),
            _ => unreachable!(),
        };
        let (target, fresh) = self.pick_workspace(&mut state, &owner)?;
        state.preferred.insert(owner.clone(), target);
        self.workspace.store.save(&state)?;
        self.workspace
            .select_session(&mut state, target, fresh, true)?;
        if let Some(old) = previous.filter(|id| id.0 != owner) {
            if self.workspace.active()? != target || !self.visible_scratchpad()?.is_empty() {
                return Err("new desktop not confirmed; previous session retained".into());
            }
            let live = Sessions::parse(&self.request(&["list"])?)?;
            if live.active_session_id.as_ref().map(|id| id.0.as_str()) != Some(owner.as_str())
                || !live.sessions.iter().any(|s| s.id.0 == owner)
            {
                return Err("new session not confirmed; previous session retained".into());
            }
            if live.contains(&old) && self.session_empty(&original_ownership, &old)? {
                let stopped = self.request(&["stop", &old.0])?;
                if stopped["stopped_session_id"].as_str() != Some(old.0.as_str()) {
                    return Err("uncertain previous-session stop; no retry".into());
                }
                let after = Sessions::parse(&self.request(&["list"])?)?;
                if after.contains(&old)
                    || after.active_session_id.as_ref().map(|id| id.0.as_str())
                        != Some(owner.as_str())
                {
                    return Err("replacement stop outcome changed; inspect state, no retry".into());
                }
                self.forget_session(&mut state, &old)?;
            }
        }
        Ok(reply)
    }
}
