//! Ordered per-owner workspace policy. No core lifecycle request is made here.
use crate::{
    Result,
    native::{self, Native},
    state::{self, MAX_ID, State},
    storage::Store,
};
use serde_json::{Value, json};
use std::{collections::BTreeSet, time::Duration};

#[derive(Clone, Debug, PartialEq)]
pub enum Action {
    Cycle,
    CreateEmpty,
    IsolateOrPrevious,
    MoveNext,
    Cleanup,
    Snapshot,
    Migrate,
    Closed(i64),
    FocusWorkspace(i64),
}
impl Action {
    pub fn parse(args: &[String]) -> Result<Self> {
        match args {
            [name]=>match name.as_str() {"cycle"=>Ok(Self::Cycle),"create-empty"=>Ok(Self::CreateEmpty),"isolate-or-previous"=>Ok(Self::IsolateOrPrevious),"move-next"=>Ok(Self::MoveNext),"cleanup"=>Ok(Self::Cleanup),"snapshot"=>Ok(Self::Snapshot),"migrate"=>Ok(Self::Migrate),_=>Err("unknown workspace command".into())},
            [name,id] if !id.is_empty() && id.bytes().all(|c|c.is_ascii_digit()) => {
                let id=id.parse::<i64>().map_err(|_|"workspace argument out of range")?;
                match name.as_str(){"closed"=>Ok(Self::Closed(id)),"focus-workspace"=>Ok(Self::FocusWorkspace(id)),_=>Err("unknown workspace command".into())}
            },
            _=>Err("usage: workspace-controller cycle|create-empty|isolate-or-previous|move-next|cleanup|snapshot|migrate|closed ID|focus-workspace ID".into())
        }
    }
}
fn array(value: Value) -> Result<Vec<Value>> {
    value
        .as_array()
        .cloned()
        .ok_or("invalid native array".into())
}
fn id(value: &Value) -> Result<i64> {
    value
        .get("id")
        .and_then(Value::as_i64)
        .ok_or("missing native workspace ID".into())
}
fn client_ws(value: &Value) -> i64 {
    value
        .get("workspace")
        .and_then(|v| v.get("id"))
        .and_then(Value::as_i64)
        .unwrap_or(0)
}

pub struct Controller<N: Native, S: Store> {
    pub native: N,
    pub store: S,
}
impl<N: Native, S: Store> Controller<N, S> {
    pub fn active(&mut self) -> Result<i64> {
        id(&self.native.query("activeworkspace")?)
    }
    fn existing(&mut self) -> Result<BTreeSet<i64>> {
        let ids: BTreeSet<i64> = array(self.native.query("workspaces")?)?
            .iter()
            .map(id)
            .filter(|v| !matches!(v,Ok(n) if *n<=0))
            .collect::<Result<_>>()?;
        if ids.iter().any(|id| *id > MAX_ID) {
            return Err("native workspace ID limit exceeded".into());
        }
        Ok(ids)
    }
    fn occupied(&mut self) -> Result<BTreeSet<i64>> {
        Ok(array(self.native.query("clients")?)?
            .iter()
            .map(client_ws)
            .filter(|ws| *ws > 0)
            .collect())
    }
    fn visible(&mut self) -> Result<BTreeSet<i64>> {
        let mut visible: BTreeSet<_> = array(self.native.query("monitors")?)?
            .iter()
            .filter_map(|v| {
                v.get("activeWorkspace")
                    .and_then(|v| v.get("id"))
                    .and_then(Value::as_i64)
            })
            .collect();
        visible.insert(self.active()?);
        visible.remove(&0);
        Ok(visible)
    }
    pub fn read_state(&mut self) -> Result<State> {
        let existing = self.existing()?;
        let mut state = state::project(self.store.read()?, &existing)?;
        for ws in existing
            .iter()
            .filter(|ws| !state.order.contains(ws))
            .copied()
            .collect::<Vec<_>>()
        {
            state.order.push(ws);
            state.owners.insert(ws.to_string(), "neutral".into());
        }
        state.next_id = state.next_id.max(existing.last().copied().unwrap_or(0) + 1);
        state.validate()?;
        Ok(state)
    }
    pub fn load(&mut self) -> Result<State> {
        let state = self.read_state()?;
        self.store.save(&state)?;
        Ok(state)
    }
    pub fn cleanup(&mut self, state: &mut State) -> Result<()> {
        let mut keep = self.occupied()?;
        keep.extend(self.visible()?);
        state.order.retain(|ws| keep.contains(ws));
        state
            .owners
            .retain(|ws, _| state.order.iter().any(|id| id.to_string() == *ws));
        state
            .preferred
            .retain(|_, ws| keep.contains(ws) && state.owners.contains_key(&ws.to_string()));
        self.store.save(state)
    }
    pub fn fresh_workspace(
        &mut self,
        state: &mut State,
        owner: &str,
        after: Option<i64>,
    ) -> Result<i64> {
        let existing = self.existing()?;
        let maximum = existing
            .iter()
            .chain(state.order.iter())
            .copied()
            .max()
            .unwrap_or(0);
        let ws = state.next_id.max(maximum + 1);
        if ws > MAX_ID {
            return Err("workspace ID limit exceeded".into());
        }
        let index = after
            .and_then(|a| state.order.iter().position(|ws| *ws == a))
            .map(|i| i + 1)
            .unwrap_or(state.order.len());
        state.next_id = ws + 1;
        state.order.insert(index, ws);
        state.owners.insert(ws.to_string(), owner.into());
        Ok(ws)
    }
    fn discard_reservation(&mut self, state: &mut State, ws: i64) -> Result<()> {
        state.order.retain(|id| *id != ws);
        state.owners.remove(&ws.to_string());
        state.preferred.retain(|_, id| *id != ws);
        self.store.save(state)
    }
    pub fn select(
        &mut self,
        state: &mut State,
        ws: i64,
        fresh: bool,
        cleanup_after: bool,
    ) -> Result<()> {
        state.preferred.insert(state.owner(ws).into(), ws);
        self.store.save(state)?;
        let expression = native::focus(ws, fresh);
        if let Err(e) = self
            .native
            .ctl(&[if fresh { "eval" } else { "dispatch" }, &expression])
        {
            if fresh {
                self.discard_reservation(state, ws)
                    .map_err(|cleanup| format!("{e}; reservation save failed: {cleanup}"))?;
            }
            return Err(e);
        }
        if cleanup_after {
            self.cleanup(state)?;
        }
        Ok(())
    }
    pub fn cycle(&mut self, state: &mut State) -> Result<()> {
        let current = self.active()?;
        if current <= 0 {
            return Ok(());
        }
        self.cleanup(state)?;
        let targets: Vec<_> = state
            .order
            .iter()
            .copied()
            .filter(|ws| state.owner(*ws) == state.owner(current))
            .collect();
        if let Some(index) = targets.iter().position(|ws| *ws == current) {
            self.select(state, targets[(index + 1) % targets.len()], false, true)?;
        }
        Ok(())
    }
    pub fn create_empty(&mut self, state: &mut State) -> Result<()> {
        let current = self.active()?;
        if current <= 0 {
            return Ok(());
        }
        self.cleanup(state)?;
        if !self.occupied()?.contains(&current) {
            let index = state
                .order
                .iter()
                .position(|ws| *ws == current)
                .ok_or("current workspace is not registered")?;
            if let Some(previous) = state.order[..index]
                .iter()
                .rev()
                .find(|ws| state.owner(**ws) == state.owner(current))
                .copied()
            {
                self.select(state, previous, false, true)?;
            }
            return Ok(());
        }
        let owner = state.owner(current).to_owned();
        let ws = self.fresh_workspace(state, &owner, Some(current))?;
        self.select(state, ws, true, true)
    }
    fn movement_source(&mut self, state: &mut State) -> Result<Option<(i64, String)>> {
        let client = self.native.query("activewindow")?;
        let ws = client_ws(&client);
        let address = client.get("address").and_then(Value::as_str).unwrap_or("");
        if ws <= 0 || address.is_empty() {
            return Ok(None);
        }
        self.cleanup(state)?;
        Ok(Some((ws, address.into())))
    }
    fn transfer(
        &mut self,
        state: &mut State,
        source: i64,
        address: &str,
        target: i64,
        fresh: bool,
    ) -> Result<()> {
        if source == target || state.owner(source) != state.owner(target) {
            return Err("unsafe workspace transfer".into());
        }
        state.preferred.insert(state.owner(target).into(), target);
        self.store.save(state)?;
        let result = native::move_window(target, address, fresh).and_then(|expression| {
            self.native
                .ctl(&[if fresh { "eval" } else { "dispatch" }, &expression])
        });
        if let Err(e) = result {
            if fresh {
                self.discard_reservation(state, target)
                    .map_err(|cleanup| format!("{e}; reservation save failed: {cleanup}"))?;
            }
            return Err(e);
        }
        self.cleanup(state)
    }
    pub fn isolate_or_previous(&mut self, state: &mut State) -> Result<()> {
        let Some((ws, address)) = self.movement_source(state)? else {
            return Ok(());
        };
        let count = array(self.native.query("clients")?)?
            .iter()
            .filter(|v| client_ws(v) == ws)
            .count();
        if count > 1 {
            let owner = state.owner(ws).to_owned();
            let target = self.fresh_workspace(state, &owner, Some(ws))?;
            return self.transfer(state, ws, &address, target, true);
        }
        let occupied = self.occupied()?;
        let index = state
            .order
            .iter()
            .position(|id| *id == ws)
            .ok_or("source workspace is not registered")?;
        if let Some(target) = state.order[..index]
            .iter()
            .rev()
            .find(|target| occupied.contains(target) && state.owner(**target) == state.owner(ws))
            .copied()
        {
            self.transfer(state, ws, &address, target, false)?;
        }
        Ok(())
    }
    pub fn move_next(&mut self, state: &mut State) -> Result<()> {
        let Some((ws, address)) = self.movement_source(state)? else {
            return Ok(());
        };
        let targets: Vec<_> = state
            .order
            .iter()
            .copied()
            .filter(|id| state.owner(*id) == state.owner(ws))
            .collect();
        if targets.len() > 1 {
            let index = targets
                .iter()
                .position(|id| *id == ws)
                .ok_or("source workspace is not registered")?;
            self.transfer(
                state,
                ws,
                &address,
                targets[(index + 1) % targets.len()],
                false,
            )?;
        }
        Ok(())
    }
    pub fn closed(&mut self, state: &mut State, ws: i64) -> Result<()> {
        if ws <= 0 || !state.owners.contains_key(&ws.to_string()) {
            return Ok(());
        }
        let mut empty = false;
        for _ in 0..40 {
            if !array(self.native.query("clients")?)?
                .iter()
                .any(|v| client_ws(v) == ws)
            {
                empty = true;
                break;
            }
            // Historical CLOSE-WAIT-001: tracked separately, not silently fixed by R1.
            self.native.sleep(Duration::from_millis(50));
        }
        if !empty {
            return Ok(());
        }
        let occupied = self.occupied()?;
        if occupied.contains(&ws) {
            return Ok(());
        }
        let candidates: Vec<_> = state
            .order
            .iter()
            .copied()
            .filter(|id| occupied.contains(id) && state.owner(*id) == state.owner(ws))
            .collect();
        if self.active()? == ws && !candidates.is_empty() {
            let index = state
                .order
                .iter()
                .position(|id| *id == ws)
                .ok_or("closed workspace missing")?;
            let previous = state.order[..index]
                .iter()
                .rev()
                .find(|id| candidates.contains(id))
                .copied();
            self.select(state, previous.unwrap_or(candidates[0]), false, true)
        } else {
            self.cleanup(state)
        }
    }
    pub fn snapshot(&mut self) -> Result<Value> {
        let state = self.read_state()?;
        let current = self.active()?;
        let mut keep = self.occupied()?;
        keep.extend(self.visible()?);
        let rows: Vec<_> = state
            .order
            .iter()
            .filter(|id| keep.contains(id) && state.owner(**id) == state.owner(current))
            .enumerate()
            .map(|(i, id)| json!({"id":id,"name":(i+1).to_string()}))
            .collect();
        Ok(json!({"active_workspace_id":current,"workspaces":rows}))
    }
    pub fn dismiss_scratchpad(&mut self) -> Result<bool> {
        let monitors = array(self.native.query("monitors")?)?;
        let monitor = monitors
            .iter()
            .find(|m| m.get("focused").and_then(Value::as_bool) == Some(true))
            .or_else(|| {
                if monitors.len() == 1 {
                    monitors.first()
                } else {
                    None
                }
            })
            .ok_or("cannot determine focused monitor; refusing navigation")?;
        let name = monitor
            .get("specialWorkspace")
            .and_then(|v| v.get("name"))
            .and_then(Value::as_str)
            .unwrap_or("");
        if name.is_empty() {
            return Ok(false);
        }
        let suffix = name
            .strip_prefix("special:")
            .filter(|s| {
                !s.is_empty()
                    && s.len() <= 100
                    && s.bytes()
                        .all(|c| c.is_ascii_alphanumeric() || c == b'_' || c == b'-')
            })
            .ok_or("unsafe special workspace name; refusing navigation")?;
        self.native.ctl(&[
            "dispatch",
            &format!("hl.dsp.workspace.toggle_special(\"{suffix}\")"),
        ])?;
        Ok(true)
    }
    /// Caller owns the workspace lock. No nested process acquires that lock.
    pub fn run(&mut self, action: Action) -> Result<Option<Value>> {
        if matches!(
            action,
            Action::Cycle | Action::CreateEmpty | Action::FocusWorkspace(_)
        ) && self.dismiss_scratchpad()?
        {
            return Ok(None);
        }
        if action == Action::Snapshot {
            return self.snapshot().map(Some);
        }
        let mut state = self.load()?;
        match action {
            Action::Cycle => self.cycle(&mut state)?,
            Action::CreateEmpty => self.create_empty(&mut state)?,
            Action::IsolateOrPrevious => self.isolate_or_previous(&mut state)?,
            Action::MoveNext => self.move_next(&mut state)?,
            Action::Cleanup => self.cleanup(&mut state)?,
            Action::Closed(ws) => self.closed(&mut state, ws)?,
            Action::FocusWorkspace(ws) => {
                self.cleanup(&mut state)?;
                let active = self.active()?;
                if state.order.contains(&ws) && state.owner(ws) == state.owner(active) {
                    self.select(&mut state, ws, false, true)?;
                }
            }
            Action::Migrate => {}
            Action::Snapshot => unreachable!(),
        }
        Ok(None)
    }
}
