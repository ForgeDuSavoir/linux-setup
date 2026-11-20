//! Private, bounded usage data. No mutation until a confirmed accepted launch.
use crate::{Application, Result, fs, git};
use serde::{
    Deserialize, Serialize,
    de::{self, MapAccess, Visitor},
};
use std::collections::BTreeMap;
use std::fmt;
use std::path::{Path, PathBuf};

pub const LIMIT: usize = 1024 * 1024;
const MAX_ENTRIES: usize = 4096;
const RETENTION: u64 = 180 * 86400;
const MAX_DATE: u64 = 253402300799;

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Entry {
    pub count: u64,
    pub last_used: u64,
    pub weight: f64,
}
impl Entry {
    pub fn score(&self, now: u64) -> f64 {
        self.weight * 2f64.powf(-(now.saturating_sub(self.last_used) as f64) / 604800.0)
    }
}
#[derive(Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct History {
    version: u64,
    #[serde(deserialize_with = "unique_apps")]
    pub apps: BTreeMap<String, Entry>,
}
fn unique_apps<'de, D: de::Deserializer<'de>>(
    d: D,
) -> std::result::Result<BTreeMap<String, Entry>, D::Error> {
    struct Unique;
    impl<'de> Visitor<'de> for Unique {
        type Value = BTreeMap<String, Entry>;
        fn expecting(&self, f: &mut fmt::Formatter) -> fmt::Result {
            f.write_str("unique bounded app IDs")
        }
        fn visit_map<M: MapAccess<'de>>(
            self,
            mut map: M,
        ) -> std::result::Result<Self::Value, M::Error> {
            let mut entries = BTreeMap::new();
            while let Some((key, value)) = map.next_entry::<String, Entry>()? {
                if entries.len() >= MAX_ENTRIES || entries.insert(key, value).is_some() {
                    return Err(de::Error::custom("duplicate/excess app IDs"));
                }
            }
            Ok(entries)
        }
    }
    d.deserialize_map(Unique)
}
impl Default for History {
    fn default() -> Self {
        Self {
            version: 1,
            apps: BTreeMap::new(),
        }
    }
}
impl History {
    pub fn parse(bytes: &[u8]) -> Result<Self> {
        if bytes.len() > LIMIT {
            return Err("usage file exceeds 1 MiB".into());
        }
        let value: Self =
            serde_json::from_slice(bytes).map_err(|_| "invalid usage JSON/schema/duplicate key")?;
        if value.version != 1 {
            return Err("unsupported usage version; preserving file".into());
        }
        for (id, entry) in &value.apps {
            if !valid_id(id)
                || entry.count == 0
                || entry.last_used > MAX_DATE
                || !entry.weight.is_finite()
                || entry.weight <= 0.0
                || entry.weight > (entry.count as f64).min(1_000_000.0)
            {
                return Err("invalid usage entry".into());
            }
        }
        Ok(value)
    }
    pub fn compare(&self, a: (&str, &str), b: (&str, &str), now: u64) -> std::cmp::Ordering {
        let rank = |id: &str| {
            self.apps
                .get(id)
                .map(|e| (e.score(now), e.last_used.min(now)))
                .unwrap_or((0.0, 0))
        };
        let ar = rank(a.0);
        let br = rank(b.0);
        br.0.total_cmp(&ar.0)
            .then_with(|| br.1.cmp(&ar.1))
            .then_with(|| a.1.to_lowercase().cmp(&b.1.to_lowercase()))
            .then_with(|| a.0.cmp(b.0))
    }
    fn update(&mut self, id: &str, now: u64) -> Result<Vec<u8>> {
        if !valid_id(id) || now > MAX_DATE {
            return Err("invalid usage ID/time".into());
        }
        let entry = self.apps.entry(id.into()).or_insert(Entry {
            count: 0,
            last_used: now,
            weight: 0.0,
        });
        entry.weight = (entry.score(now) + 1.0).min(1_000_000.0);
        entry.count = entry.count.saturating_add(1);
        entry.last_used = now;
        self.apps
            .retain(|key, e| key == id || now.saturating_sub(e.last_used) <= RETENTION);
        let mut eviction: Vec<_> = self
            .apps
            .iter()
            .filter(|(key, _)| key.as_str() != id)
            .map(|(key, e)| (e.last_used.min(now), key.clone()))
            .collect();
        eviction.sort();
        let mut evict = eviction.into_iter();
        loop {
            let bytes = serde_json::to_vec(self).map_err(|_| "cannot serialize usage")?;
            if self.apps.len() <= MAX_ENTRIES && bytes.len() <= LIMIT {
                return Ok(bytes);
            }
            let (_, key) = evict.next().ok_or("usage file cannot fit limits")?;
            self.apps.remove(&key);
        }
    }
}
pub fn valid_id(id: &str) -> bool {
    id.len() <= 1024
        && id != ".desktop"
        && id.ends_with(".desktop")
        && !id.contains(['/', '\\'])
        && !id.chars().any(char::is_control)
}
pub fn now() -> Result<u64> {
    let time = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_err(|_| "clock before Unix epoch")?
        .as_secs();
    if time > MAX_DATE {
        return Err("clock exceeds supported date range".into());
    }
    Ok(time)
}

pub struct Store {
    directory: PathBuf,
    data: &'static str,
    lock: &'static str,
    project: Option<(PathBuf, fs::Identity)>,
}
impl Store {
    pub fn project(path: &Path, id: fs::Identity) -> Self {
        Self {
            directory: path.join(".session-manager"),
            data: "app-usage.json",
            lock: "app-usage.lock",
            project: Some((path.into(), id)),
        }
    }
    pub fn global(home: &Path, neutral: bool) -> Result<Self> {
        let base = std::env::var_os("XDG_STATE_HOME")
            .filter(|s| !s.is_empty())
            .map(PathBuf::from)
            .unwrap_or_else(|| home.join(".local/state"));
        if !base.is_absolute() {
            return Err("XDG_STATE_HOME must be absolute; usage disabled".into());
        }
        Ok(Self {
            directory: base.join("session-app-launcher"),
            data: if neutral {
                "neutral.json"
            } else {
                "unowned.json"
            },
            lock: if neutral {
                "neutral.lock"
            } else {
                "unowned.lock"
            },
            project: None,
        })
    }
    fn directory(&self, create: bool) -> std::io::Result<fs::Dir> {
        let dir = if let Some((path, id)) = &self.project {
            let root = fs::Dir::open(path, false)?;
            root.own()?;
            if root.id()? != *id {
                return Err(std::io::Error::other("project directory replaced"));
            }
            root.child(std::ffi::OsStr::new(".session-manager"), create)?
        } else {
            fs::Dir::open(&self.directory, create)?
        };
        dir.own()?;
        Ok(dir)
    }
    pub fn read(&self) -> Result<History> {
        let dir = match self.directory(false) {
            Ok(d) => d,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(History::default()),
            Err(e) => return Err(e.to_string()),
        };
        let (bytes, _) = dir
            .read(self.data, LIMIT, false)
            .map_err(|e| e.to_string())?;
        bytes
            .map(|b| History::parse(&b))
            .unwrap_or_else(|| Ok(History::default()))
    }
    #[cfg(test)]
    pub fn record(&self, app: &Application, time: u64) -> Result<()> {
        self.record_checked(app, time, || Ok(()))
    }
    pub fn record_checked(
        &self,
        app: &Application,
        time: u64,
        check: impl FnOnce() -> Result<()>,
    ) -> Result<()> {
        let dir = self.directory(true).map_err(|e| e.to_string())?;
        git::ensure_excluded(&self.directory, self.data, self.lock)?;
        let _lock = dir.lock(self.lock).map_err(|e| e.to_string())?;
        let (bytes, stamp) = dir
            .read(self.data, LIMIT, false)
            .map_err(|e| e.to_string())?;
        let mut value = bytes
            .map(|b| History::parse(&b))
            .unwrap_or_else(|| Ok(History::default()))?;
        let updated = value.update(&app.id, time)?;
        // The pathname must still denote the same directory capability.
        if self
            .directory(false)
            .map_err(|e| e.to_string())?
            .id()
            .map_err(|e| e.to_string())?
            != dir.id().map_err(|e| e.to_string())?
        {
            return Err("usage directory moved/replaced".into());
        }
        check()?; // Last context check after exclusion work and lock contention.
        dir.publish(
            self.data,
            &updated,
            stamp.as_ref(),
            false,
            ".app-usage.tmp-",
        )
        .map_err(|e| e.to_string())
    }
}

#[cfg(test)]
#[path = "history_tests.rs"]
mod tests;
