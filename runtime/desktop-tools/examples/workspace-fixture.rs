//! Test-only in-memory native adapter; never spawns a compositor or reads HOME.
use agora_desktop_tools::{
    Result,
    native::Native,
    state::{self, State},
    storage::Store,
    workspace::{Action, Controller},
};
use serde_json::{Value, json};
use std::{
    collections::BTreeSet,
    io::{self, Read},
    time::Duration,
};
struct Memory {
    raw: Option<Value>,
    saves: usize,
    fail_save: usize,
}
impl Store for Memory {
    fn read(&mut self) -> Result<Option<Value>> {
        Ok(self.raw.clone())
    }
    fn save(&mut self, s: &State) -> Result<()> {
        s.validate()?;
        self.saves += 1;
        if self.saves == self.fail_save {
            return Err("injected write failure".into());
        }
        self.raw = Some(serde_json::to_value(s).unwrap());
        Ok(())
    }
}
struct World {
    value: Value,
    codes: Vec<Value>,
    sleeps: usize,
}
impl World {
    fn active(&self) -> i64 {
        self.value["active"].as_i64().unwrap()
    }
    fn ids(&self) -> BTreeSet<i64> {
        self.value["ws"]
            .as_array()
            .unwrap()
            .iter()
            .map(|v| v.as_i64().unwrap())
            .collect()
    }
    fn prune(&mut self) {
        let mut ids: BTreeSet<i64> = self.value["clients"]
            .as_array()
            .unwrap()
            .iter()
            .map(|c| c["workspace"]["id"].as_i64().unwrap())
            .filter(|ws| *ws > 0)
            .collect();
        ids.insert(self.active());
        for id in self.value["other_visible"].as_array().unwrap() {
            ids.insert(id.as_i64().unwrap());
        }
        self.value["ws"] = json!(ids);
    }
    fn event(&mut self, e: Value) {
        self.value["events"].as_array_mut().unwrap().push(e);
    }
    fn focus(&mut self, ws: i64) {
        self.event(json!(["focus", ws]));
        self.value["active"] = json!(ws);
        self.value["focused"] = self.value["clients"]
            .as_array()
            .unwrap()
            .iter()
            .find(|c| c["workspace"]["id"] == ws)
            .map(|c| c["address"].clone())
            .unwrap_or(Value::Null);
        self.prune();
    }
}
impl Native for World {
    fn query(&mut self, name: &str) -> Result<Value> {
        if self.value["fail_query"] == name {
            return Err("injected query failure".into());
        }
        Ok(match name {
            "clients" => self.value["clients"].clone(),
            "activeworkspace" => json!({"id":self.active()}),
            "activewindow" => self.value["clients"]
                .as_array()
                .unwrap()
                .iter()
                .find(|c| c["address"] == self.value["focused"])
                .cloned()
                .unwrap_or(json!({})),
            "workspaces" => json!(
                self.ids()
                    .iter()
                    .map(|id| json!({"id":id}))
                    .collect::<Vec<_>>()
            ),
            "monitors" => {
                if let Some(monitors) = self.value.get("monitors") {
                    return Ok(monitors.clone());
                }
                let mut rows = vec![
                    json!({"focused":true,"activeWorkspace":{"id":self.active()},"specialWorkspace":{"name":self.value.get("special").and_then(Value::as_str).unwrap_or("")}}),
                ];
                rows.extend(self.value["other_visible"].as_array().unwrap().iter().map(|id|json!({"focused":false,"activeWorkspace":{"id":id},"specialWorkspace":{"name":""}})));
                json!(rows)
            }
            _ => return Err("unexpected query".into()),
        })
    }
    fn ctl(&mut self, args: &[&str]) -> Result<String> {
        let (kind, code) = (args[0], args[1]);
        self.codes.push(json!([kind, code]));
        if code.contains("toggle_special") {
            self.event(json!(["hide", code]));
            self.value["special"] = json!("");
            return Ok("ok".into());
        }
        let ws = code
            .split("workspace = ")
            .nth(1)
            .ok_or("missing target")?
            .split(|c: char| !c.is_ascii_digit())
            .next()
            .unwrap()
            .parse::<i64>()
            .map_err(|_| "bad target")?;
        let mode = self.value["failure"].as_str().unwrap_or("").to_owned();
        if kind == "eval"
            && code.contains("workspace target already exists")
            && (self.ids().contains(&ws) || mode == "race")
        {
            return Err("workspace target already exists".into());
        }
        if mode == "reject" {
            return Err("injected native rejection".into());
        }
        if code.contains("window.move") {
            let address = code
                .split("address:")
                .nth(1)
                .ok_or("missing address")?
                .split('"')
                .next()
                .unwrap();
            let address = address.to_owned();
            self.event(json!(["move", ws, address]));
            let client = self.value["clients"]
                .as_array_mut()
                .unwrap()
                .iter_mut()
                .find(|c| c["address"] == address)
                .ok_or("missing moving window")?;
            client["workspace"] = json!({"id":ws,"name":ws.to_string()});
        }
        self.focus(ws);
        if mode == "lost" {
            return Err("lost acknowledgement".into());
        }
        Ok("ok".into())
    }
    fn sleep(&mut self, _: Duration) {
        self.sleeps += 1;
    }
}
fn main() {
    let mut text = String::new();
    io::stdin().read_to_string(&mut text).unwrap();
    let input: Value = serde_json::from_str(&text).unwrap();
    let mut c = Controller {
        native: World {
            value: input["world"].clone(),
            codes: vec![],
            sleeps: 0,
        },
        store: Memory {
            raw: input.get("raw").filter(|v| !v.is_null()).cloned(),
            saves: 0,
            fail_save: input["fail_save"].as_u64().unwrap_or(0) as usize,
        },
    };
    let existing = c.native.ids();
    let mut state = state::project(input.get("state").cloned(), &existing);
    let result: Result<Value> = (|| {
        for step in input["steps"].as_array().unwrap() {
            let op = step["op"].as_str().unwrap();
            let ws = step["ws"].as_i64().unwrap_or(1);
            if op == "project" {
                return serde_json::to_value(state.as_ref().map_err(Clone::clone)?)
                    .map_err(|e| e.to_string());
            }
            if op == "read" {
                state = Ok(c.read_state()?);
                continue;
            }
            if op == "load" {
                state = Ok(c.load()?);
                continue;
            }
            if op == "snapshot" {
                return c.snapshot();
            }
            if op == "run" {
                let args: Vec<String> = step["args"]
                    .as_array()
                    .unwrap()
                    .iter()
                    .map(|s| s.as_str().unwrap().to_owned())
                    .collect();
                return Ok(c.run(Action::parse(&args)?)?.unwrap_or(Value::Null));
            }
            let s = state.as_mut().map_err(|e| e.clone())?;
            match op {
                "cycle" => c.cycle(s)?,
                "create-empty" => c.create_empty(s)?,
                "isolate-or-previous" => c.isolate_or_previous(s)?,
                "move-next" => c.move_next(s)?,
                "cleanup" => c.cleanup(s)?,
                "closed" => c.closed(s, ws)?,
                "fresh" => {
                    c.fresh_workspace(s, "A", Some(ws))?;
                }
                _ => return Err("unknown operation".into()),
            }
        }
        Ok(Value::Null)
    })();
    println!(
        "{}",
        json!({"ok":result.is_ok(),"output":result.as_ref().ok(),"error":result.as_ref().err(),"state":state.ok(),"raw":c.store.raw,"world":c.native.value,"sleeps":c.native.sleeps,"codes":c.native.codes})
    );
}
