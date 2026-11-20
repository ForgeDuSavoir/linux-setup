//! Pure workspace projection; no native requests, ownership adoption or IO.
use crate::Result;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::{BTreeMap, BTreeSet};

pub const MAX_ID: i64 = 2_147_483_646;

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct State {
    pub version: u64,
    pub order: Vec<i64>,
    pub owners: BTreeMap<String, String>,
    pub preferred: BTreeMap<String, i64>,
    pub next_id: i64,
    #[serde(flatten)]
    pub extra: BTreeMap<String, Value>,
}
impl State {
    pub fn validate(&self) -> Result<()> {
        let ids: BTreeSet<_> = self.order.iter().copied().collect();
        if self.version != 3
            || ids.len() != self.order.len()
            || ids.iter().any(|id| !(1..=MAX_ID).contains(id))
            || self.owners.keys().cloned().collect::<BTreeSet<_>>()
                != ids.iter().map(i64::to_string).collect()
            || self.owners.values().any(String::is_empty)
            || !(1..=MAX_ID + 1).contains(&self.next_id)
            || self
                .preferred
                .iter()
                .any(|(owner, ws)| !ids.contains(ws) || self.owner(*ws) != owner)
        {
            return Err("invalid workspace state".into());
        }
        Ok(())
    }
    pub fn owner(&self, ws: i64) -> &str {
        self.owners
            .get(&ws.to_string())
            .map(String::as_str)
            .unwrap_or("neutral")
    }
    pub fn from_value(mut value: Value) -> Result<Self> {
        if let Some(object) = value.as_object_mut() {
            object.remove("origins");
        }
        let state: Self =
            serde_json::from_value(value).map_err(|e| format!("invalid workspace state: {e}"))?;
        state.validate()?;
        Ok(state)
    }
}

pub fn project(raw: Option<Value>, existing: &BTreeSet<i64>) -> Result<State> {
    if existing.iter().any(|id| !(1..=MAX_ID).contains(id)) {
        return Err("invalid existing workspace ID".into());
    }
    let Some(raw) = raw.filter(|v| !v.is_null()) else {
        let state = State {
            version: 3,
            order: existing.iter().copied().collect(),
            owners: existing
                .iter()
                .map(|id| (id.to_string(), "neutral".into()))
                .collect(),
            preferred: BTreeMap::new(),
            next_id: existing.last().copied().unwrap_or(0) + 1,
            extra: BTreeMap::new(),
        };
        state.validate()?;
        return Ok(state);
    };
    match raw.get("version").and_then(Value::as_u64) {
        Some(3) => State::from_value(raw),
        Some(2) => {
            let empty = serde_json::Map::new();
            let owners = match raw.get("owners") {
                None => &empty,
                Some(v) => v.as_object().ok_or("invalid legacy owners")?,
            };
            let last = match raw.get("last") {
                None => &empty,
                Some(v) => v.as_object().ok_or("invalid legacy rows")?,
            };
            let mut cols: BTreeSet<i64> = existing.iter().map(|ws| (ws + 1) / 2).collect();
            for key in owners.keys() {
                let col: i64 = key.parse().map_err(|_| "invalid legacy column")?;
                if !(1..=MAX_ID / 2).contains(&col) {
                    return Err("invalid legacy column".into());
                }
                cols.insert(col);
            }
            let mut state = State {
                version: 3,
                order: Vec::new(),
                owners: BTreeMap::new(),
                preferred: BTreeMap::new(),
                next_id: 1,
                extra: BTreeMap::new(),
            };
            let mut choices = BTreeMap::new();
            for col in cols {
                let key = col.to_string();
                let row = last
                    .get(&key)
                    .map(|v| v.as_i64().ok_or("invalid legacy row"))
                    .transpose()?
                    .unwrap_or(1);
                if !matches!(row, 1 | 2) {
                    return Err("invalid legacy row".into());
                }
                let preferred = 2 * col - 2 + row;
                let mut members: Vec<_> = [2 * col - 1, 2 * col]
                    .into_iter()
                    .filter(|ws| existing.contains(ws))
                    .collect();
                if members.is_empty() {
                    members.push(preferred);
                }
                choices.insert(
                    col,
                    if members.contains(&preferred) {
                        preferred
                    } else {
                        members[0]
                    },
                );
                let owner = owners
                    .get(&key)
                    .map(|v| v.as_str().ok_or("invalid legacy owner"))
                    .transpose()?
                    .unwrap_or("neutral");
                for ws in members {
                    state.order.push(ws);
                    state.owners.insert(ws.to_string(), owner.into());
                }
            }
            if let Some(preferred) = raw.get("preferred") {
                for (owner, col) in preferred.as_object().ok_or("invalid legacy preference")? {
                    if let Some(ws) = col.as_i64().and_then(|c| choices.get(&c))
                        && state.owner(*ws) == owner
                    {
                        state.preferred.insert(owner.clone(), *ws);
                    }
                }
            }
            state.next_id = state.order.iter().max().copied().unwrap_or(0) + 1;
            state.validate()?;
            Ok(state)
        }
        _ => Err("unsupported workspace state".into()),
    }
}
