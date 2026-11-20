//! R0 dependency/API feasibility only: no production commands or installation.
#[cfg(test)]
mod tests {
    use num_bigint::BigInt;
    use num_rational::BigRational;
    use std::io::{Cursor, Read, Write};

    #[test]
    fn json_preserves_large_integers() {
        let text = "{\"ticks\":123456789012345678901234567890}";
        let value: serde_json::Value = serde_json::from_str(text).unwrap();
        assert_eq!(serde_json::to_string(&value).unwrap(), text);
    }

    #[test]
    fn config_reads_toml_one_point_zero() {
        let config: toml::Value = toml::from_str("agora_root = '/tmp/synthetic agora'").unwrap();
        assert_eq!(config["agora_root"].as_str(), Some("/tmp/synthetic agora"));
    }

    #[test]
    fn zip_metadata_round_trip() {
        let mut writer = zip::ZipWriter::new(Cursor::new(Vec::new()));
        writer
            .start_file("manifest.json", zip::write::SimpleFileOptions::default())
            .unwrap();
        writer.write_all(b"{}").unwrap();
        let data = writer.finish().unwrap();
        let mut archive = zip::ZipArchive::new(Cursor::new(data.into_inner())).unwrap();
        let mut contents = String::new();
        archive
            .by_name("manifest.json")
            .unwrap()
            .read_to_string(&mut contents)
            .unwrap();
        assert_eq!(contents, "{}");
    }

    #[test]
    fn rational_timing_and_pcm_wav() {
        let fps = BigRational::new(BigInt::from(30000), BigInt::from(1001));
        let frame = fps.recip();
        assert_eq!(frame * fps, BigRational::from_integer(BigInt::from(1)));
        let mut cursor = Cursor::new(Vec::new());
        let spec = hound::WavSpec {
            channels: 2,
            sample_rate: 48000,
            bits_per_sample: 16,
            sample_format: hound::SampleFormat::Int,
        };
        let mut wav = hound::WavWriter::new(&mut cursor, spec).unwrap();
        wav.write_sample(0_i16).unwrap();
        wav.write_sample(0_i16).unwrap();
        wav.finalize().unwrap();
        let reader = hound::WavReader::new(Cursor::new(cursor.into_inner())).unwrap();
        assert_eq!(reader.duration(), 1);
        assert_eq!(reader.spec().channels, 2);
        assert!(std::hint::black_box(libc::O_NOFOLLOW) > 0);
    }
}
