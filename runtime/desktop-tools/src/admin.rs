//! Pure installer interface: no filesystem/native/core/lock access.
use crate::{
    Result, startup,
    state::{self, State},
};
use serde_json::{Value, json};
use std::collections::BTreeSet;
pub fn run(operation: &str, input: Value) -> Result<Value> {
    match operation {
        "capabilities" => Ok(
            json!({"version":1,"runtime_version":env!("CARGO_PKG_VERSION"),"core_protocol":3,"desktop_schema":3,"marker_schema":1,"operations":["capabilities","project-state","validate-state","defer-marker"]}),
        ),
        "project-state" => {
            let ids: Vec<i64> = serde_json::from_value(
                input
                    .get("existing_ids")
                    .cloned()
                    .ok_or("missing existing_ids")?,
            )
            .map_err(|_| "invalid existing_ids")?;
            let set: BTreeSet<_> = ids.iter().copied().collect();
            if set.len() != ids.len() {
                return Err("duplicate existing workspace IDs".into());
            }
            serde_json::to_value(state::project(input.get("raw").cloned(), &set)?)
                .map_err(|e| e.to_string())
        }
        "validate-state" => {
            let raw = input.get("state").cloned().ok_or("missing state")?;
            State::from_value(raw.clone())?;
            Ok(raw)
        }
        "defer-marker" => startup::defer_marker(
            input
                .get("instance")
                .and_then(Value::as_str)
                .ok_or("missing instance")?,
            input.get("previous").cloned(),
        ),
        _ => Err("unknown admin operation".into()),
    }
}
