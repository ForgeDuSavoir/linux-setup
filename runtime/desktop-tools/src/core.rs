//! Public v3 CLI transport and typed wire envelopes. No desktop policy in the core.
use crate::{Result, process};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::{collections::BTreeSet, path::PathBuf, process::Command, time::Duration};

#[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(try_from = "String", into = "String")]
pub struct SessionId(pub String);
impl TryFrom<String> for SessionId {
    type Error = String;
    fn try_from(s: String) -> Result<Self> {
        if s.is_empty() {
            Err("empty session identity".into())
        } else {
            Ok(Self(s))
        }
    }
}
impl From<SessionId> for String {
    fn from(s: SessionId) -> String {
        s.0
    }
}
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum Source {
    Neutral {},
    Project { project_name: String },
}
impl Source {
    pub fn arguments(&self) -> Result<Vec<String>> {
        match self {
            Self::Neutral {} => Ok(vec!["--neutral".into()]),
            Self::Project { project_name } if !project_name.is_empty() => {
                Ok(vec!["--project".into(), project_name.clone()])
            }
            _ => Err("invalid v3 launch source".into()),
        }
    }
}
#[derive(Debug, Deserialize)]
pub struct Session {
    pub id: SessionId,
    pub source: Source,
}
#[derive(Debug, Deserialize)]
pub struct Sessions {
    pub sessions: Vec<Session>,
    pub active_session_id: Option<SessionId>,
}
impl Sessions {
    pub fn parse(value: &Value) -> Result<Self> {
        if value.get("active_session_id").is_none() {
            return Err("missing active session identity".into());
        }
        let parsed: Self = serde_json::from_value(value.clone())
            .map_err(|e| format!("invalid v3 session list: {e}"))?;
        let ids: BTreeSet<_> = parsed.sessions.iter().map(|s| &s.id).collect();
        if ids.len() != parsed.sessions.len()
            || parsed
                .active_session_id
                .as_ref()
                .is_some_and(|id| !ids.contains(id))
        {
            return Err("invalid session identities".into());
        }
        for session in &parsed.sessions {
            session.source.arguments()?;
        }
        Ok(parsed)
    }
    pub fn contains(&self, id: &SessionId) -> bool {
        self.sessions.iter().any(|s| &s.id == id)
    }
}
pub fn acknowledged_session(value: &Value) -> Result<SessionId> {
    let row = value
        .get("session")
        .ok_or("invalid session acknowledgement")?;
    if let Some(source) = row.get("source") {
        let source: Source =
            serde_json::from_value(source.clone()).map_err(|_| "invalid acknowledgement source")?;
        source.arguments()?;
    }
    serde_json::from_value(
        row.get("id")
            .cloned()
            .ok_or("missing acknowledgement identity")?,
    )
    .map_err(|e| e.to_string())
}
pub const REQUEST_TIMEOUT: Duration = Duration::from_secs(35);
pub trait Core {
    fn request(&mut self, args: &[&str], timeout: Duration) -> Result<Value>;
}
pub struct CliCore {
    pub binary: PathBuf,
}
impl Core for CliCore {
    fn request(&mut self, args: &[&str], timeout: Duration) -> Result<Value> {
        let output = process::run(
            Command::new(&self.binary)
                .args(["--json", "session"])
                .args(args),
            None,
            true,
            Some(timeout),
        )?;
        let value: Value =
            serde_json::from_slice(&output.stdout).map_err(|_| "invalid Session Manager reply")?;
        if !output.status.success() {
            return Err(value
                .get("code")
                .and_then(Value::as_str)
                .unwrap_or("session request failed")
                .into());
        }
        Ok(value)
    }
}
