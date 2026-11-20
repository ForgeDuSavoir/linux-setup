//! Closed, fresh FilmCraft projects only; exact timing, no GUI/desktop dependencies.
mod publication;
#[cfg(test)]
mod tests;
use num_bigint::BigInt;
use num_rational::BigRational as Rational;
use num_traits::{One, Signed, Zero};
pub use publication::{Original, Published, Temporary};
use serde_json::{Value, json};
use std::{
    fs,
    io::Write,
    path::{Path, PathBuf},
    process::{Command, Stdio},
};
pub type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;

pub fn integer(value: &Value) -> Result<BigInt> {
    if !value.is_number() {
        return Err("entier JSON attendu".into());
    }
    value
        .to_string()
        .parse()
        .map_err(|_| "entier JSON attendu".into())
}
fn positive(value: &Value) -> Result<BigInt> {
    let i = integer(value)?;
    if i <= BigInt::zero() {
        return Err("base temporelle non positive".into());
    }
    Ok(i)
}
fn array<'a>(v: &'a Value, key: &str) -> Result<&'a Vec<Value>> {
    v.get(key)
        .and_then(Value::as_array)
        .ok_or_else(|| format!("liste {key} manquante").into())
}
fn key(v: &Value) -> Result<String> {
    match v {
        Value::String(s) => Ok(s.clone()),
        Value::Number(_) => Ok(integer(v)?.to_string()),
        _ => Err("identifiant invalide".into()),
    }
}
pub fn sequence(raw: &Value) -> Result<&Value> {
    let sequences: Vec<_> = raw["project"]["items"]
        .as_object()
        .ok_or("items manquants")?
        .values()
        .filter_map(|item| item["kind"].get("Sequence"))
        .collect();
    if sequences.len() != 1 {
        return Err("une seule séquence FilmCraft est requise".into());
    }
    Ok(sequences[0])
}
fn media_path<'a>(raw: &'a Value, item: &Value) -> Result<&'a str> {
    raw["project"]["items"][key(item)?]["kind"]["Media"]["media"]["File"]["path"]
        .as_str()
        .ok_or("chemin média absent".into())
}
pub struct Timing {
    pub fps: Rational,
    pub required: Rational,
}
pub fn validate(before: &Value, raw: &Value, source: &Path, project: &Path) -> Result<Timing> {
    let tracks = array(before, "audio")?;
    if tracks.len() != 4
        || array(before, "video")?.is_empty()
        || array(&tracks[2], "items")?.is_empty()
    {
        return Err("Attendu : quatre pistes audio non vides et une vidéo".into());
    }
    let count = array(&tracks[2], "items")?.len();
    for t in tracks {
        if array(t, "items")?.len() != count {
            return Err("Les quatre pistes n'ont pas le même nombre de clips".into());
        }
    }
    for i in 0..count {
        for field in ["start", "duration", "sourceIn", "item"] {
            let first = tracks[0]["items"][i].get(field).ok_or("clip incomplet")?;
            if tracks
                .iter()
                .any(|t| t["items"][i].get(field) != Some(first))
            {
                return Err("Les pistes audio ne sont pas alignées".into());
            }
        }
    }
    let item = &tracks[2]["items"][0]["item"];
    if array(&tracks[2], "items")?
        .iter()
        .any(|c| c.get("item") != Some(item))
    {
        return Err(
            "Audio 3 contient plusieurs médias ; projet neuf mono-enregistrement requis".into(),
        );
    }
    if project
        .parent()
        .ok_or("dossier projet absent")?
        .join(media_path(raw, item)?)
        .canonicalize()?
        != source
    {
        return Err("Le média d'Audio 3 n'est pas l'enregistrement fourni".into());
    }
    let seq = sequence(raw)?;
    let raw_tracks = array(seq, "audio_tracks")?;
    if raw_tracks.len() != 4 {
        return Err("Structure du projet inattendue".into());
    }
    for (index, t) in raw_tracks.iter().enumerate() {
        if t["name"] != format!("Audio {}", index + 1)
            || array(t, "items")?
                .iter()
                .any(|c| c.get("source_channels") != Some(&json!([index])))
        {
            return Err("Canaux ou noms de pistes inattendus".into());
        }
    }
    let fps = Rational::new(
        positive(&seq["settings"]["frame_rate"]["num"])?,
        positive(&seq["settings"]["frame_rate"]["den"])?,
    );
    let ticks = Rational::new(
        positive(&before["duration"])?,
        positive(&before["durationFrames"])?,
    );
    let mut required = Rational::zero();
    for clip in array(&tracks[2], "items")? {
        let out = integer(&clip["sourceOut"])?;
        if out.is_negative() {
            return Err("sourceOut négatif".into());
        }
        required = required.max(Rational::from_integer(out) / &ticks / &fps);
    }
    Ok(Timing { fps, required })
}
pub fn verify_cuts(before: &Value, after: &Value, audio_item: &Value) -> Result<()> {
    let tracks = array(before, "audio")?;
    let new = array(after, "audio")?;
    if after.get("durationFrames") != before.get("durationFrames")
        || new.len() != 3
        || new.iter().any(|t| t["id"] == tracks[3]["id"])
        || after.get("video") != before.get("video")
    {
        return Err("Durée, vidéo ou pistes audio incorrectes après patch".into());
    }
    for i in 0..3 {
        if new[i]["id"] != tracks[i]["id"] {
            return Err("Identité de piste modifiée".into());
        }
        let old = array(&tracks[i], "items")?;
        let new_items = array(&new[i], "items")?;
        if old.len() != new_items.len() {
            return Err("Nombre de coupes modifié".into());
        }
        for (a, b) in old.iter().zip(new_items) {
            for field in ["clip", "start", "duration", "sourceIn", "sourceOut", "link"] {
                if a.get(field).is_none() || a.get(field) != b.get(field) {
                    return Err(format!("Coupes modifiées sur Audio {}", i + 1).into());
                }
            }
            if b.get("item")
                != Some(if i == 2 {
                    audio_item
                } else {
                    a.get("item").ok_or("source manquante")?
                })
            {
                return Err("Source incorrecte après patch".into());
            }
        }
    }
    Ok(())
}
pub fn verify_raw(
    raw_before: &Value,
    raw_after: &Value,
    audio_item: &Value,
    wav_name: &str,
) -> Result<()> {
    if media_path(raw_after, audio_item)? != wav_name {
        return Err("Chemin WAV non relatif".into());
    }
    let before_seq = sequence(raw_before)?;
    let after_seq = sequence(raw_after)?;
    let original = array(before_seq, "audio_tracks")?;
    let patched = array(after_seq, "audio_tracks")?;
    if patched.len() != 3 || patched.iter().any(|t| t["id"] == original[3]["id"]) {
        return Err("Audio 4 n'a pas été supprimée".into());
    }
    if original[..2] != patched[..2] {
        return Err("Pistes micro modifiées".into());
    }
    if array(&patched[2], "items")?
        .iter()
        .any(|c| !c["source_channels"].is_null() && c["source_channels"] != json!([0, 1]))
    {
        return Err("Audio 3 n'est pas stéréo".into());
    }
    Ok(())
}
/// Exact nearest decimal, ties-to-even. Floating point is never a timing authority.
pub fn decimal(value: &Rational, places: u32) -> Result<String> {
    if value.is_negative() {
        return Err("durée négative".into());
    }
    let scale = BigInt::from(10u8).pow(places);
    let scaled = value.numer() * &scale;
    let mut whole = &scaled / value.denom();
    let rest = &scaled % value.denom();
    let twice = rest * 2;
    if twice > *value.denom() || (twice == *value.denom() && (&whole % 2u8) == BigInt::one()) {
        whole += 1;
    }
    let digits = whole.to_string();
    if places == 0 {
        return Ok(digits);
    }
    let padded = format!("{:0>width$}", digits, width = places as usize + 1);
    let (a, b) = padded.split_at(padded.len() - places as usize);
    Ok(format!("{a}.{b}"))
}
fn run(command: &mut Command, input: Option<&str>) -> Result<Vec<u8>> {
    command
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .stdin(if input.is_some() {
            Stdio::piped()
        } else {
            Stdio::inherit()
        });
    let mut child = command.spawn()?;
    std::thread::scope(|scope| -> Result<_> {
        let writer = input.map(|data| {
            let mut pipe = child.stdin.take().unwrap();
            scope.spawn(move || pipe.write_all(data.as_bytes()))
        });
        let output = child.wait_with_output()?;
        let written = writer
            .map(|t| t.join().map_err(|_| "écriture CLI interrompue"))
            .transpose()?;
        if !output.status.success() {
            return Err(format!(
                "Commande {:?} échouée : {} {}",
                command.get_program(),
                String::from_utf8_lossy(&output.stderr),
                String::from_utf8_lossy(&output.stdout)
            )
            .into());
        }
        if let Some(w) = written {
            w?;
        }
        Ok(output.stdout)
    })
}
fn fc(project: &Path, parent: &Path, args: &[&str], input: Option<&str>) -> Result<Value> {
    let bytes = run(
        Command::new("filmcraft-cli")
            .arg("--project")
            .arg(project)
            .args(args)
            .current_dir(parent),
        input,
    )?;
    Ok(serde_json::from_slice(&bytes)?)
}
fn inspect(project: &Path, parent: &Path) -> Result<Value> {
    fc(project, parent, &["inspect", "sequence"], None)
}
pub fn wav_duration(path: &Path) -> Result<Rational> {
    let reader = hound::WavReader::open(path)?;
    let spec = reader.spec();
    if spec.channels != 2
        || spec.sample_rate == 0
        || spec.bits_per_sample != 16
        || spec.sample_format != hound::SampleFormat::Int
    {
        return Err("WAV bureau attendu : PCM16 stéréo".into());
    }
    Ok(Rational::new(
        reader.duration().into(),
        spec.sample_rate.into(),
    ))
}
pub struct Outcome {
    pub wav: PathBuf,
    pub backup: PathBuf,
    pub clips: usize,
}
pub fn patch(source: &Path, project: &Path) -> Result<Outcome> {
    let source = source.canonicalize()?;
    let project = project.canonicalize()?;
    if source.to_str().is_none() || project.to_str().is_none() {
        return Err("Chemins non UTF-8 non supportés par JSON FilmCraft".into());
    }
    if !source.is_file() || !project.is_file() {
        return Err("Enregistrement ou projet FilmCraft introuvable".into());
    }
    let parent = project.parent().ok_or("Dossier projet absent")?;
    if source.parent() != Some(parent) || source == project {
        return Err("Enregistrement et projet distincts requis dans le même dossier".into());
    }
    let original = Original::open(&project)?;
    let streams: Value = serde_json::from_slice(&run(
        Command::new("ffprobe")
            .args([
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=channels",
                "-of",
                "json",
            ])
            .arg(&source),
        None,
    )?)?;
    let rows = array(&streams, "streams")?;
    if rows.len() != 2 || rows.iter().any(|s| s["channels"] != json!(2)) {
        return Err("Attendu : exactement deux flux audio stéréo (micro puis bureau)".into());
    }
    let before = inspect(&project, parent)?;
    let raw: Value = serde_json::from_slice(&original.bytes)?;
    let timing = validate(&before, &raw, &source, &project)?;
    let wav_name = format!(
        "{}_bureau.wav",
        source
            .file_stem()
            .ok_or("nom d'enregistrement absent")?
            .to_str()
            .ok_or("nom non UTF-8")?
    );
    let wav = parent.join(&wav_name);
    if wav.symlink_metadata().is_ok() {
        return Err("WAV déjà présent, ne sera pas écrasé".into());
    }
    let mut extracted = Temporary::new(parent, ".filmcraft-bureau-", ".wav")?;
    run(
        Command::new("ffmpeg")
            .args(["-hide_banner", "-loglevel", "error", "-y", "-i"])
            .arg(&source)
            .args([
                "-map",
                "0:a:1",
                "-vn",
                "-af",
                "aresample=async=1:first_pts=0",
                "-c:a",
                "pcm_s16le",
            ])
            .arg(&extracted.path),
        None,
    )?;
    extracted.refresh()?;
    if fs::metadata(&extracted.path)?.len() < 1000 {
        return Err("Extraction du flux bureau vide".into());
    }
    let audio = wav_duration(&extracted.path)?;
    let shortage = &timing.required - audio;
    if shortage > Rational::new(1.into(), 5.into()) {
        return Err(format!(
            "Flux bureau trop court de {} s (> 0,2 s)",
            decimal(&shortage, 3)?
        )
        .into());
    }
    if shortage > Rational::zero() {
        let mut padded = Temporary::new(parent, ".filmcraft-pad-", ".wav")?;
        let target = &timing.required + Rational::one() / &timing.fps;
        run(
            Command::new("ffmpeg")
                .args(["-hide_banner", "-loglevel", "error", "-y", "-i"])
                .arg(&extracted.path)
                .args([
                    "-af",
                    "apad",
                    "-t",
                    &decimal(&target, 9)?,
                    "-c:a",
                    "pcm_s16le",
                ])
                .arg(&padded.path),
            None,
        )?;
        padded.refresh()?;
        if wav_duration(&padded.path)? <= timing.required {
            return Err("Silence final insuffisant pour les dernières coupes".into());
        }
        std::mem::swap(&mut extracted, &mut padded);
        println!(
            "ℹ️ Bureau plus court que les coupes de {} s ; fin complétée par du silence.",
            decimal(&shortage, 3)?
        );
    }
    let published = Published::create(&extracted, &wav).map_err(|e| {
        format!(
            "{e}; vérifier l’existence et l’identité de {} avant reprise.",
            wav.display()
        )
    })?;
    let result = (|| -> Result<Outcome> {
        let mut temp = Temporary::new(parent, ".filmcraft-original-", ".fcproj")?;
        let import = json!({"paths":[wav]}).to_string();
        run(
            Command::new("filmcraft-cli")
                .arg("--project")
                .arg(&project)
                .arg("--save-as")
                .arg(&temp.path)
                .args(["exec", "file.import", &import])
                .current_dir(parent),
            None,
        )?;
        temp.refresh()?;
        let tree = fc(&temp.path, parent, &["inspect", "project"], None)?;
        let matches: Vec<_> = array(&tree["root"], "children")?
            .iter()
            .filter(|i| i["name"] == wav_name && i["type"] == "Audio")
            .collect();
        if matches.len() != 1 {
            return Err("Import WAV non confirmé".into());
        }
        let audio_item = matches[0].get("item").ok_or("item audio absent")?.clone();
        let relink = json!({"item":audio_item,"path":wav_name,"relinkOthers":false}).to_string();
        let relinked = fc(
            &temp.path,
            parent,
            &["--save", "exec", "media.relink", &relink],
            None,
        )?;
        temp.refresh()?;
        if array(&relinked, "relinked")?.len() != 1
            || relinked["relinked"][0]["path"] != wav_name
            || !array(&relinked, "remaining")?.is_empty()
        {
            return Err("Liaison relative du WAV non confirmée".into());
        }
        let tracks = array(&before, "audio")?;
        let steps = [
            json!({"id":"sequence.linkedSelection","params":{"on":false}}),
            json!({"id":"clip.replaceFromBin","params":{"clips":array(&tracks[2],"items")?.iter().map(|c|c["clip"].clone()).collect::<Vec<_>>(),"item":audio_item,"keepSourceIn":true}}),
            json!({"id":"sequence.deleteTrack","params":{"track":tracks[3]["id"]}}),
            json!({"id":"sequence.linkedSelection","params":{"on":true}}),
        ];
        let input = steps.iter().map(|v| format!("{v}\n")).collect::<String>();
        let output = run(
            Command::new("filmcraft-cli")
                .arg("--project")
                .arg(&temp.path)
                .args(["--save", "run", "-"])
                .current_dir(parent),
            Some(&input),
        )?;
        temp.refresh()?;
        let text = std::str::from_utf8(&output)?;
        let rows: Vec<Value> = text
            .lines()
            .filter(|l| !l.trim().is_empty())
            .map(serde_json::from_str)
            .collect::<std::result::Result<_, _>>()?;
        if rows.len() != 4 || rows.iter().any(|r| r["ok"] != json!(true)) {
            return Err("Résultat inattendu du patch".into());
        }
        let replaced = &rows[1]["result"];
        if array(replaced, "clips")?.len() != array(&tracks[2], "items")?.len()
            || replaced.get("short").is_some_and(truthy)
            || replaced.get("sourceInClamped").is_some_and(truthy)
        {
            return Err("Remplacement incomplet ou audio trop court".into());
        }
        let after = inspect(&temp.path, parent)?;
        verify_cuts(&before, &after, &audio_item)?;
        let missing = fc(&temp.path, parent, &["exec", "media.findMissing"], None)?;
        if missing.get("missing").is_some_and(truthy) {
            return Err("Des médias manquent dans le projet patché".into());
        }
        let check: Value = serde_json::from_slice(&temp.bytes()?)?;
        verify_raw(&raw, &check, &audio_item, &wav_name)?;
        published.verify()?;
        original.verify()?;
        temp.verify()?;
        let backup = original.exchange(&mut temp)?;
        Ok(Outcome {
            wav: wav.clone(),
            backup,
            clips: array(&tracks[2], "items")?.len(),
        })
    })();
    result.map_err(|e|format!("{e}; WAV publié conservé : {}. Inspecter avant toute reprise ; aucun rollback/rejeu automatique.",wav.display()).into())
}
fn truthy(v: &Value) -> bool {
    match v {
        Value::Null => false,
        Value::Bool(b) => *b,
        Value::Array(a) => !a.is_empty(),
        Value::Object(o) => !o.is_empty(),
        Value::String(s) => !s.is_empty(),
        Value::Number(n) => n.as_i64() != Some(0),
    }
}
