fn main() {
    let args: Vec<_> = std::env::args_os().skip(1).collect();
    if args == ["--version"] {
        println!(
            "filmcraft-patch-desktop-audio {} (Rust; exact stereo stream)",
            env!("CARGO_PKG_VERSION")
        );
        return;
    }
    let result = if args.len() == 2 {
        filmcraft_desktop_audio::patch(args[0].as_ref(), args[1].as_ref())
    } else {
        Err("Usage : filmcraft-patch-desktop-audio recording.mkv premontage.fcproj (projet neuf fermé)".into())
    };
    match result {
        Ok(out) => println!(
            "✅ Son du bureau restauré sur Audio 3 : {} clips ; Audio 4 supprimée.\n   WAV : {}\n   Projet original conservé : {}",
            out.clips,
            out.wav.display(),
            out.backup.display()
        ),
        Err(e) => {
            eprintln!("❌ Patch audio FilmCraft : {e}");
            std::process::exit(1);
        }
    }
}
