//! Two-image thumbnail orchestration. No GUI, Python or desktop dependencies.
use serde_json::{Value, json};
use std::{
    collections::BTreeSet,
    ffi::{CStr, CString},
    fs::{self, File},
    io::{Read, Write},
    os::unix::{ffi::OsStrExt, fs::MetadataExt},
    path::{Path, PathBuf},
    process::{Command, Stdio},
};
use zip::{ZipArchive, ZipWriter, write::SimpleFileOptions};
pub type Result<T> = std::result::Result<T, Box<dyn std::error::Error>>;
pub const OUTPUT: &str = "miniature.pcraft";
pub const MASK: &str = "photocraft-thumbnail-mask.zip";
#[cfg(test)]
mod tests;

pub fn crop(width: u64, height: u64) -> Result<(u64, u64)> {
    if width < 1920
        || !width.is_multiple_of(16)
        || width
            .checked_mul(10)
            .zip(height.checked_mul(16))
            .is_none_or(|(a, b)| a != b)
        || width.checked_mul(9).is_none()
    {
        return Err(format!(
            "attendu au moins 1920 px de large au format exact 16:10, obtenu {width}x{height}"
        )
        .into());
    }
    let crop = width * 9 / 16;
    if crop > height || !(height - crop).is_multiple_of(2) {
        return Err("recadrage 16:9 centré impossible avec des pixels entiers".into());
    }
    Ok((crop, (height - crop) / 2))
}
pub fn mean(bytes: &[u8]) -> Result<f64> {
    if bytes.len() != 1024 {
        return Err("Impossible de mesurer la luminosité (attendu : 1024 octets)".into());
    }
    Ok(bytes.iter().map(|b| u64::from(*b)).sum::<u64>() as f64 / 1024.)
}
pub fn choose(scores: [f64; 2]) -> Result<usize> {
    let top = if scores[0] <= scores[1] { 0 } else { 1 };
    let dark = scores[top];
    let bright = scores[1 - top];
    if !dark.is_finite() || !bright.is_finite() || bright - dark < 15. || dark > bright * 0.75 {
        return Err("Différence de luminosité insuffisante ; relancer avec --top 'nom-exact-de-l-image.png'".into());
    }
    Ok(top)
}
pub fn expand(path: &str) -> Result<PathBuf> {
    if !path.starts_with('~') {
        return Ok(path.into());
    }
    let (user, rest) = path[1..].split_once('/').unwrap_or((&path[1..], ""));
    if user.is_empty()
        && let Some(home) = std::env::var_os("HOME")
    {
        return Ok(PathBuf::from(home).join(rest));
    }
    // Reentrant passwd lookup; do not read profiles or infer Agora directories.
    let name = CString::new(user)?;
    let mut buffer = vec![0u8; 16384];
    loop {
        let mut pwd = std::mem::MaybeUninit::<libc::passwd>::uninit();
        let mut found = std::ptr::null_mut();
        let code = unsafe {
            if user.is_empty() {
                libc::getpwuid_r(
                    libc::getuid(),
                    pwd.as_mut_ptr(),
                    buffer.as_mut_ptr().cast(),
                    buffer.len(),
                    &mut found,
                )
            } else {
                libc::getpwnam_r(
                    name.as_ptr(),
                    pwd.as_mut_ptr(),
                    buffer.as_mut_ptr().cast(),
                    buffer.len(),
                    &mut found,
                )
            }
        };
        if code == libc::ERANGE {
            buffer.resize(
                buffer
                    .len()
                    .checked_mul(2)
                    .ok_or("passwd lookup too large")?,
                0,
            );
            continue;
        }
        if code != 0 || found.is_null() {
            return Err("Impossible de développer le dossier utilisateur".into());
        }
        let home = unsafe { CStr::from_ptr((*found).pw_dir) }.to_bytes();
        return Ok(PathBuf::from(std::ffi::OsStr::from_bytes(home)).join(rest));
    }
}
fn run(command: &mut Command) -> Result<Vec<u8>> {
    let result = command.stdin(Stdio::inherit()).output()?;
    if !result.status.success() {
        return Err(format!(
            "{:?} a échoué : {}",
            command.get_program(),
            String::from_utf8_lossy(if result.stderr.is_empty() {
                &result.stdout
            } else {
                &result.stderr
            })
            .trim()
        )
        .into());
    }
    Ok(result.stdout)
}
fn prepare(image: &Path, target: &Path) -> Result<()> {
    let probe: Value = serde_json::from_slice(&run(Command::new("ffprobe")
        .args([
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "json",
        ])
        .arg(image))?)?;
    let streams = probe["streams"]
        .as_array()
        .filter(|v| v.len() == 1)
        .ok_or("Impossible de lire les dimensions")?;
    let width = streams[0]["width"].as_u64().ok_or("largeur invalide")?;
    let height = streams[0]["height"].as_u64().ok_or("hauteur invalide")?;
    let (crop, top) = crop(width, height)?;
    println!(
        "{} : {width}x{height} → crop 0,{top},{width},{crop} → 1920x1080",
        image.file_name().unwrap().to_string_lossy()
    );
    run(Command::new("ffmpeg")
        .args(["-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i"])
        .arg(image)
        .args([
            "-vf",
            &format!("crop={width}:{crop}:0:{top},scale=1920:1080:flags=lanczos,format=rgba"),
            "-frames:v",
            "1",
        ])
        .arg(target))?;
    Ok(())
}
fn brightness(image: &Path) -> Result<f64> {
    mean(&run(Command::new("ffmpeg")
        .args(["-hide_banner", "-loglevel", "error", "-nostdin", "-i"])
        .arg(image)
        .args([
            "-vf",
            "crop=576:756:672:162,scale=32:32:flags=area,format=gray",
            "-frames:v",
            "1",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "gray",
            "-",
        ]))?)
}
fn read<R: Read + std::io::Seek>(archive: &mut ZipArchive<R>, name: &str) -> Result<Vec<u8>> {
    let mut data = Vec::new();
    archive.by_name(name)?.read_to_end(&mut data)?;
    Ok(data)
}
fn unique<R: Read + std::io::Seek>(archive: &ZipArchive<R>) -> Result<()> {
    if archive.has_duplicate_names() {
        return Err("Entrées ZIP dupliquées".into());
    }
    let mut seen = BTreeSet::new();
    for name in archive.file_names() {
        if !seen.insert(name?.into_owned()) {
            return Err("Entrées ZIP dupliquées".into());
        }
    }
    Ok(())
}
pub fn mask_paths(
    reference: &Value,
    document: &mut Value,
    top: &str,
    bottom: &str,
) -> Result<BTreeSet<String>> {
    if reference["format_version"] != json!(1)
        || document["format_version"] != json!(1)
        || reference["width"] != json!(1920)
        || reference["height"] != json!(1080)
        || document["document"]["size"] != json!({"width":1920,"height":1080})
    {
        return Err(
            "Format du projet ou du masque incompatible (attendu : PhotoCraft v1, 1920x1080)"
                .into(),
        );
    }
    let layers = document["document"]["layers"]
        .as_array_mut()
        .ok_or("Calques invalides")?;
    if layers.len() != 2
        || layers[0]["name"] != bottom
        || layers[1]["name"] != top
        || layers
            .iter()
            .any(|l| !l["mask"].is_null() && l["mask"] != json!(false))
    {
        return Err("Calques inattendus : impossible de poser le masque".into());
    }
    let mask = reference.get("mask").ok_or("Masque manquant")?;
    let surface = &mask["surface"];
    let tiles = surface["tiles"].as_array().ok_or("Tuiles manquantes")?;
    if surface["format"] != json!({"mode":"Grayscale","sample":"U8","alpha":false})
        || tiles.len() != 40
    {
        return Err("Masque de référence incomplet ou incompatible".into());
    }
    let mut coords = BTreeSet::new();
    let mut paths = BTreeSet::new();
    for tile in tiles {
        let tx = tile["tx"].as_u64().ok_or("Coordonnée de tuile invalide")?;
        let ty = tile["ty"].as_u64().ok_or("Coordonnée de tuile invalide")?;
        if tx >= 8 || ty >= 5 || !coords.insert((tx, ty)) {
            return Err("Coordonnées de tuiles invalides".into());
        }
        let hash = tile["hash"].as_str().ok_or("Référence de tuile invalide")?;
        if hash.len() != 64
            || !hash
                .bytes()
                .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        {
            return Err("Référence de tuile invalide".into());
        }
        paths.insert(format!("tiles/{hash}.zst"));
    }
    layers[1]["mask"] = mask.clone();
    Ok(paths)
}
pub fn apply_mask(
    template: &Path,
    project: &Path,
    output: &Path,
    top: &str,
    bottom: &str,
) -> Result<()> {
    let mut reference = ZipArchive::new(File::open(template)?)?;
    unique(&reference)?;
    let mut source = ZipArchive::new(File::open(project)?)?;
    unique(&source)?;
    let mask: Value = serde_json::from_slice(&read(&mut reference, "mask.json")?)?;
    let mut document: Value = serde_json::from_slice(&read(&mut source, "manifest.json")?)?;
    let paths = mask_paths(&mask, &mut document, top, bottom)?;
    let present: BTreeSet<String> = source
        .file_names()
        .map(|n| n.map(|s| s.into_owned()))
        .collect::<std::result::Result<_, _>>()?;
    let mut writer = ZipWriter::new(File::create_new(output)?);
    for i in 0..source.len() {
        let mut entry = source.by_index(i)?;
        let name = entry.name()?.into_owned();
        let options = entry.options();
        // Validate decompression/CRC, then preserve opaque compressed bytes/metadata.
        std::io::copy(&mut entry, &mut std::io::sink())?;
        drop(entry);
        if name == "manifest.json" {
            // LZMA reading is supported, but zip does not encode it; JSON is stored.
            writer.start_file(
                name,
                options.compression_method(zip::CompressionMethod::Stored),
            )?;
            writer.write_all(&serde_json::to_vec(&document)?)?;
        } else {
            writer.raw_copy_file(source.by_index(i)?)?;
        }
    }
    for path in paths {
        let data = read(&mut reference, &path)?;
        if present.contains(&path) {
            if read(&mut source, &path)? != data {
                return Err("Conflit de tuiles entre le projet et le masque".into());
            }
        } else {
            writer.start_file(
                path,
                SimpleFileOptions::default().compression_method(zip::CompressionMethod::Stored),
            )?;
            writer.write_all(&data)?;
        }
    }
    writer.finish()?.sync_all()?;
    Ok(())
}
pub fn verify(info: &Value, top: &str, bottom: &str) -> Result<()> {
    let layers = info["layers"].as_array().ok_or("Calques manquants")?;
    if info["width"] != json!(1920) || info["height"] != json!(1080) || layers.len() != 2 {
        return Err("Le projet ne contient pas exactement deux calques en 1920x1080".into());
    }
    for (i, name) in [top, bottom].iter().enumerate() {
        if layers[i]["name"] != *name
            || layers[i]["bounds"] != json!([0, 0, 1920, 1080])
            || layers[i]["hasMask"] != json!(i == 0)
        {
            return Err(
                "Les calques PhotoCraft ou le masque ne correspondent pas aux images préparées"
                    .into(),
            );
        }
    }
    Ok(())
}
struct Temporary {
    path: PathBuf,
    dev: u64,
    ino: u64,
}
impl Temporary {
    fn new(directory: &Path) -> Result<Self> {
        let path = directory.join(".photocraft-thumbnail-XXXXXX");
        let mut bytes = CString::new(path.as_os_str().as_bytes())?.into_bytes_with_nul();
        if unsafe { libc::mkdtemp(bytes.as_mut_ptr().cast()) }.is_null() {
            return Err(std::io::Error::last_os_error().into());
        }
        let path = PathBuf::from(std::ffi::OsStr::from_bytes(&bytes[..bytes.len() - 1]));
        let m = fs::symlink_metadata(&path)?;
        Ok(Self {
            path,
            dev: m.dev(),
            ino: m.ino(),
        })
    }
}
impl Drop for Temporary {
    fn drop(&mut self) {
        if let Ok(m) = fs::symlink_metadata(&self.path)
            && m.is_dir()
            && m.dev() == self.dev
            && m.ino() == self.ino
        {
            let _ = fs::remove_dir_all(&self.path);
        }
    }
}
pub fn generate(requested: &Path, top: Option<&str>, template: &Path) -> Result<()> {
    let directory = requested.canonicalize()?;
    if !directory.is_dir() {
        return Err("Dossier introuvable".into());
    }
    let folding: std::collections::BTreeMap<String, String> =
        serde_json::from_str(include_str!("casefold.json"))?;
    let mut images = Vec::new();
    for entry in fs::read_dir(&directory)? {
        let path = entry?.path();
        let extension = path
            .extension()
            .and_then(|s| s.to_str())
            .unwrap_or("")
            .to_ascii_lowercase();
        if path.is_file()
            && ["png", "jpg", "jpeg", "webp", "tif", "tiff", "bmp"].contains(&extension.as_str())
        {
            let name = path
                .file_name()
                .and_then(|s| s.to_str())
                .ok_or("Nom de fichier non UTF-8")?
                .to_owned();
            let folded: String = name
                .chars()
                .map(|c| {
                    folding
                        .get(&c.to_string())
                        .cloned()
                        .unwrap_or_else(|| c.to_string())
                })
                .collect();
            images.push((folded, name, path));
        }
    }
    images.sort_by(|a, b| (&a.0, &a.1).cmp(&(&b.0, &b.1)));
    if images.len() != 2 {
        return Err(format!(
            "Attendu : exactement deux images PNG/JPEG/WebP/TIFF/BMP ; trouvé {}",
            images.len()
        )
        .into());
    }
    if images.iter().any(|i| i.2.is_symlink()) {
        return Err(
            "Les images doivent être des fichiers réguliers, pas des liens symboliques".into(),
        );
    }
    let destination = directory.join(OUTPUT);
    if destination.symlink_metadata().is_ok() {
        return Err("Le projet existe déjà, il ne sera pas écrasé".into());
    }
    let temporary = Temporary::new(&directory)?;
    let temp = &temporary.path;
    let prepared = [temp.join("0.png"), temp.join("1.png")];
    for i in 0..2 {
        prepare(&images[i].2, &prepared[i])?;
    }
    let scores = [brightness(&prepared[0])?, brightness(&prepared[1])?];
    println!(
        "Luminosité au centre : {} = {:.1}, {} = {:.1}",
        images[0].1, scores[0], images[1].1, scores[1]
    );
    let top = if let Some(name) = top.filter(|s| !s.is_empty()) {
        images
            .iter()
            .position(|i| i.1 == name)
            .ok_or("--top doit être le nom exact d'une des deux images du dossier")?
    } else {
        choose(scores)?
    };
    let bottom = 1 - top;
    let project = temp.join(OUTPUT);
    run(Command::new("photocraft-cli")
        .arg("run")
        .arg(&prepared[bottom])
        .args([
            "--cmd",
            "layer.setProps",
            "--params",
            &json!({"name":images[bottom].1}).to_string(),
            "--cmd",
            "file.placeEmbedded",
            "--params",
            &json!({"path":prepared[top],"fit":false,"smartObject":false}).to_string(),
            "--cmd",
            "layer.setProps",
            "--params",
            &json!({"name":images[top].1}).to_string(),
            "--out",
        ])
        .arg(&project))?;
    if !project.is_file() || project.metadata()?.len() == 0 {
        return Err("PhotoCraft n'a pas créé le projet".into());
    }
    let masked = temp.join("masked.pcraft");
    apply_mask(
        template,
        &project,
        &masked,
        &images[top].1,
        &images[bottom].1,
    )?;
    let info: Value = serde_json::from_slice(&run(Command::new("photocraft-cli")
        .arg("info")
        .arg(&masked)
        .arg("--compact"))?)?;
    verify(&info, &images[top].1, &images[bottom].1)?;
    fs::hard_link(&masked, &destination).map_err(|e| {
        if e.kind() == std::io::ErrorKind::AlreadyExists {
            std::io::Error::new(
                e.kind(),
                "Le projet a été créé entre-temps, il ne sera pas écrasé",
            )
        } else {
            e
        }
    })?;
    println!(
        "✓ Projet créé : {}\n  En haut : {} (masque et dégradé identiques au modèle) ; en bas : {}",
        destination.display(),
        images[top].1,
        images[bottom].1
    );
    Ok(())
}
