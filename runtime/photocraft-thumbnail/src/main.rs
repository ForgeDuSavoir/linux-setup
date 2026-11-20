use photocraft_thumbnail::{MASK, Result, expand, generate};
fn main() {
    match run() {
        Ok(()) => {}
        Err((code, error)) => {
            eprintln!("photocraft-thumbnail: {error}");
            std::process::exit(code);
        }
    }
}
fn run() -> std::result::Result<(), (i32, String)> {
    let args = std::env::args_os()
        .skip(1)
        .map(|s| {
            s.into_string()
                .map_err(|_| (2, "arguments non UTF-8".into()))
        })
        .collect::<std::result::Result<Vec<_>, _>>()?;
    if args == ["--version"] {
        println!(
            "photocraft-thumbnail {} (Rust; reference mask)",
            env!("CARGO_PKG_VERSION")
        );
        return Ok(());
    }
    let mut directory = None;
    let mut top = None;
    let mut options = true;
    let mut i = 0;
    while i < args.len() {
        let arg = &args[i];
        i += 1;
        if options && ["--h", "--he", "--hel", "--help", "-h"].contains(&arg.as_str()) {
            println!(
                "Usage: photocraft-thumbnail DIRECTORY [--top EXACT_FILENAME]\nDeux images 16:10, masque de référence, miniature.pcraft sans écrasement."
            );
            return Ok(());
        }
        if options && arg == "--" {
            options = false;
            continue;
        }
        if options && arg.starts_with("--") && arg != "--" {
            let (key, value) = arg
                .split_once('=')
                .map(|(a, b)| (a, Some(b.to_owned())))
                .unwrap_or((arg, None));
            if !["--t", "--to", "--top"].contains(&key) {
                return Err((2, "option inconnue".into()));
            }
            top = Some(if let Some(v) = value {
                v
            } else {
                let v = args
                    .get(i)
                    .filter(|s| s.as_str() == "-" || !s.starts_with('-'))
                    .ok_or((2, "--top attend un nom de fichier".into()))?;
                i += 1;
                v.clone()
            });
            continue;
        }
        if options && arg.starts_with('-') && arg != "-" {
            return Err((2, "option inconnue".into()));
        }
        if directory.replace(arg.clone()).is_some() {
            return Err((2, "attendu : un seul dossier".into()));
        }
    }
    let directory = directory.ok_or((
        2,
        "usage: photocraft-thumbnail DIRECTORY [--top EXACT_FILENAME]".into(),
    ))?;
    let execute = || -> Result<()> {
        let directory = expand(&directory)?;
        let template = std::env::current_exe()?
            .parent()
            .ok_or("Dossier de l'exécutable inconnu")?
            .join(MASK);
        generate(&directory, top.as_deref(), &template)
    };
    execute().map_err(|e| (1, e.to_string()))
}
