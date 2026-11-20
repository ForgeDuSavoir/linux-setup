//! Context-confirmed Rofi launcher with private project-local usage ranking.
mod context;
mod fs;
mod git;
mod history;
mod process;
#[cfg(test)]
mod test_support;

use gio::prelude::*;
use serde::{Deserialize, de::DeserializeOwned};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::Duration;

type Result<T> = std::result::Result<T, String>;

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
enum Origin {
    Installed,
    Project,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
struct Application {
    id: String,
    name: String,
    #[serde(default)]
    icon: Option<String>,
    origin: Origin,
}

impl Application {
    fn validate(&self) -> Result<()> {
        if !history::valid_id(&self.id) {
            return Err("invalid desktop-entry ID".into());
        }
        Ok(())
    }
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(tag = "kind", rename_all = "lowercase", deny_unknown_fields)]
enum Source {
    Neutral {},
    Project { project_name: String },
}
#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
struct Session {
    id: String,
    source: Source,
}
#[derive(Deserialize)]
struct Sessions {
    sessions: Vec<Session>,
    active_session_id: Option<String>,
    revision: u64,
}
#[derive(Deserialize)]
struct Applications {
    applications: Vec<Application>,
}
#[derive(Deserialize)]
struct Project {
    name: String,
    path: PathBuf,
}
#[derive(Deserialize)]
struct Projects {
    projects: Vec<Project>,
}

struct Client {
    home: PathBuf,
    manager: PathBuf,
    theme: PathBuf,
}
impl Client {
    fn query<T: DeserializeOwned>(&self, args: &[&str]) -> Result<T> {
        let output = process::run(
            Command::new(&self.manager).arg("--json").args(args),
            None,
            true,
            Some(Duration::from_secs(35)),
        )?;
        if !output.status.success() {
            return Err("Session Manager request failed".into());
        }
        serde_json::from_slice(&output.stdout).map_err(|_| "invalid Session Manager reply".into())
    }
    fn applications(&self) -> Result<Vec<Application>> {
        let apps: Applications = self.query(&["application", "list"])?;
        let mut ids = std::collections::HashSet::new();
        for app in &apps.applications {
            app.validate()?;
            if !ids.insert(&app.id) {
                return Err("duplicate application ID".into());
            }
        }
        Ok(apps.applications)
    }
    fn store(&self, binding: &context::Binding) -> Option<history::Store> {
        let result = if let Some((path, id)) = &binding.project {
            Ok(history::Store::project(path, id.clone()))
        } else {
            history::Store::global(&self.home, binding.active.is_some())
        };
        match result {
            Ok(store) => Some(store),
            Err(error) => {
                warning(&error);
                None
            }
        }
    }
    fn launch_choice(
        &self,
        binding: &context::Binding,
        choice: &context::Choice,
        store: Option<&history::Store>,
    ) -> Result<()> {
        self.revalidate(binding, choice)?;
        let mut command = match choice.app.origin {
            Origin::Installed => {
                let mut command = Command::new("gtk-launch");
                command.arg(&choice.app.id);
                command
            }
            Origin::Project => {
                let path = &binding.project.as_ref().ok_or("project missing")?.0;
                let mut command = Command::new("gio");
                command
                    .arg("launch")
                    .arg(path.join(".session-manager/apps").join(&choice.app.id));
                command
            }
        };
        let output = process::run(&mut command, None, false, Some(Duration::from_secs(30)))?;
        if !output.status.success() {
            return Err("desktop launch rejected".into());
        }
        // Browser shortcuts deliberately bypass all usage/history work.
        if store.is_none() {
            return Ok(());
        }
        let update: Result<()> = (|| {
            self.revalidate(binding, choice)?;
            if let Some(store) = store {
                store.record_checked(&choice.app, history::now()?, || {
                    self.revalidate(binding, choice)
                })?;
            }
            Ok(())
        })();
        if let Err(error) = update {
            warning(&error);
        }
        Ok(())
    }
    fn run(&self, browser: bool) -> Result<()> {
        let mut snapshot = self.snapshot()?;
        if browser {
            let choice = snapshot
                .choices
                .iter()
                .find(|c| c.app.id == "firefox.desktop")
                .ok_or("Firefox is unavailable in the current context")?;
            return self.launch_choice(&snapshot.binding, choice, None);
        }
        if snapshot.choices.is_empty() {
            return Ok(());
        }
        let store = self.store(&snapshot.binding);
        let mut usage = store
            .as_ref()
            .map(|s| s.read())
            .unwrap_or_else(|| Ok(history::History::default()))
            .unwrap_or_else(|error| {
                warning(&error);
                history::History::default()
            });
        let now = match history::now() {
            Ok(time) => time,
            Err(error) => {
                warning(&error);
                usage = history::History::default();
                0
            }
        };
        snapshot.choices.sort_by(|a, b| {
            usage.compare(
                (&a.app.id, &clean(&a.info.name)),
                (&b.app.id, &clean(&b.info.name)),
                now,
            )
        });
        let rows: String = snapshot
            .choices
            .iter()
            .map(|c| row(&c.app, c.info.clone()))
            .collect();
        let output = process::run(
            Command::new("rofi")
                .args([
                    "-dmenu",
                    "-markup-rows",
                    "-i",
                    "-no-custom",
                    "-show-icons",
                    "-no-sort",
                    "-format",
                    "i",
                    "-theme",
                ])
                .arg(&self.theme)
                .args(["-p", "Apps"]),
            Some(rows.as_bytes()),
            true,
            None,
        )?;
        if !output.status.success() {
            return Ok(());
        }
        let index = std::str::from_utf8(&output.stdout)
            .map_err(|_| "invalid launcher selection")?
            .trim()
            .parse::<usize>()
            .map_err(|_| "invalid launcher selection")?;
        self.launch_choice(
            &snapshot.binding,
            snapshot
                .choices
                .get(index)
                .ok_or("invalid launcher selection")?,
            store.as_ref(),
        )
    }
}

#[derive(Clone, Debug)]
struct Metadata {
    name: String,
    generic: String,
    keywords: Vec<String>,
    comment: String,
}
impl Metadata {
    fn read(app: &Application, project: Option<&Path>) -> Self {
        let entry = match app.origin {
            Origin::Installed => gio::DesktopAppInfo::new(&app.id),
            Origin::Project => project.and_then(|p| {
                let path = p.join(".session-manager/apps").join(&app.id);
                if path.is_symlink() {
                    None
                } else {
                    gio::DesktopAppInfo::from_filename(path)
                }
            }),
        };
        if let Some(entry) = entry {
            Self {
                name: entry.name().to_string(),
                generic: entry
                    .generic_name()
                    .map(|s| s.to_string())
                    .unwrap_or_default(),
                keywords: entry.keywords().iter().map(|s| s.to_string()).collect(),
                comment: entry
                    .description()
                    .map(|s| s.to_string())
                    .unwrap_or_default(),
            }
        } else {
            Self {
                name: app.name.clone(),
                generic: String::new(),
                keywords: vec![],
                comment: String::new(),
            }
        }
    }
}

fn clean(value: &str) -> String {
    value
        .chars()
        .map(|c| {
            if (c as u32) < 32 || c == '\u{7f}' {
                ' '
            } else {
                c
            }
        })
        .collect()
}
fn escape(value: &str) -> String {
    clean(value)
        .replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
        .replace('\'', "&#x27;")
}
fn row(app: &Application, info: Metadata) -> String {
    let mut label = escape(&info.name);
    if !info.generic.is_empty() {
        label += &format!(
            " <span weight='light' size='small'><i>({})</i></span>",
            escape(&info.generic)
        );
    }
    let search = clean(
        &[
            vec![info.generic, info.comment],
            info.keywords,
            vec![app.id.clone()],
        ]
        .concat()
        .into_iter()
        .filter(|s| !s.is_empty())
        .collect::<Vec<_>>()
        .join(" "),
    );
    let mut result = format!("{label}\0meta\x1f{search}");
    if let Some(icon) = &app.icon
        && !icon.is_empty()
        && !icon.chars().any(|c| (c as u32) < 32)
    {
        result += &format!("\x1ficon\x1f{icon}");
    }
    result + "\n"
}
#[cfg(test)]
fn menu_rows(apps: &[Application], project: Option<&Path>) -> String {
    apps.iter()
        .map(|app| row(app, Metadata::read(app, project)))
        .collect()
}
fn warning(error: &str) {
    eprintln!("Session application launcher: usage update unavailable/skipped: {error}");
}
fn main() {
    if let Err(error) = entry() {
        eprintln!("Session application launcher: {error}");
        std::process::exit(1);
    }
}
fn entry() -> Result<()> {
    let args = std::env::args_os().skip(1).collect::<Vec<_>>();
    if args == ["--version"] {
        println!(
            "session-app-launcher {} (Rust; project-local usage history v1)",
            env!("CARGO_PKG_VERSION")
        );
        return Ok(());
    }
    let browser = args == ["--browser"];
    if !args.is_empty() && !browser {
        return Err("usage: session-app-launcher [--browser]".into());
    }
    let home = std::env::var_os("HOME")
        .map(PathBuf::from)
        .filter(|p| p.is_absolute())
        .ok_or("HOME must be absolute")?;
    let client = Client {
        manager: home.join(".local/bin/session-manager"),
        theme: home.join(".config/rofi/project-launcher.rasi"),
        home,
    };
    client.run(browser)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn app(id: &str) -> Application {
        Application {
            id: id.into(),
            name: "Fallback".into(),
            icon: Some("icon".into()),
            origin: Origin::Installed,
        }
    }
    #[test]
    fn markup_and_search_are_separate() {
        let text = row(
            &app("a.desktop"),
            Metadata {
                name: "<b>&\n'\"".into(),
                generic: "Calculator".into(),
                keywords: vec!["arithmetic".into()],
                comment: "bad\0value".into(),
            },
        );
        assert!(text.starts_with("&lt;b&gt;&amp; &#x27;&quot;"));
        assert!(text.contains("<i>(Calculator)</i>"));
        assert!(text.contains("\0meta\x1fCalculator bad value arithmetic a.desktop"));
        assert_eq!(text.matches('\0').count(), 1);
    }
    #[test]
    fn identifiers_are_not_paths_or_controls() {
        for id in [
            "../x.desktop",
            "x/y.desktop",
            "x\\y.desktop",
            "bad",
            "a\n.desktop",
            ".desktop",
        ] {
            assert!(app(id).validate().is_err());
        }
        assert!(app("org.example.App.desktop").validate().is_ok());
    }
    #[test]
    fn sources_are_closed() {
        assert!(
            serde_json::from_str::<Source>(r#"{"kind":"neutral","project_name":"P"}"#).is_err()
        );
        assert_eq!(
            serde_json::from_str::<Source>(r#"{"kind":"neutral"}"#).unwrap(),
            Source::Neutral {}
        );
    }
    #[test]
    fn missing_metadata_and_bad_icon_match_legacy() {
        let mut app = app("nonexistent-fixture.desktop");
        app.name = "One\nTwo".into();
        app.icon = Some("bad\nicon".into());
        assert_eq!(
            menu_rows(&[app], None),
            "One Two\0meta\x1fnonexistent-fixture.desktop\n"
        );
    }
}
