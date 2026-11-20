use super::*;
fn reference() -> Value {
    serde_json::from_slice(
        &read(
            &mut ZipArchive::new(std::io::Cursor::new(include_bytes!(
                "../../../scripts/photocraft-thumbnail/photocraft-thumbnail-mask.zip"
            )))
            .unwrap(),
            "mask.json",
        )
        .unwrap(),
    )
    .unwrap()
}
fn document() -> Value {
    json!({"format_version":1,"document":{"size":{"width":1920,"height":1080},"layers":[{"name":"bottom","mask":null},{"name":"top","mask":null}],"extra":"preserved"}})
}
#[test]
fn crop_examples() {
    assert_eq!(crop(2880, 1800).unwrap(), (1620, 90));
    assert_eq!(crop(2304, 1440).unwrap(), (1296, 72));
    assert_eq!(crop(1920, 1200).unwrap(), (1080, 60));
}
#[test]
fn crop_refusals() {
    for (w, h) in [
        (1600, 1000),
        (1920, 1080),
        (1936, 1210),
        (0, 0),
        (u64::MAX, u64::MAX),
    ] {
        assert!(crop(w, h).is_err());
    }
}
#[test]
fn mean_exact() {
    assert_eq!(mean(&[50; 1024]).unwrap(), 50.);
    assert_eq!(mean(&[255; 1024]).unwrap(), 255.);
}
#[test]
fn mean_size_refusal() {
    assert!(mean(&[0; 1023]).is_err());
    assert!(mean(&[]).is_err());
}
#[test]
fn threshold_edges() {
    assert_eq!(choose([45., 60.]).unwrap(), 0);
    assert_eq!(choose([60., 45.]).unwrap(), 1);
    assert!(choose([46., 61.]).is_err());
    assert!(choose([44., 58.]).is_err());
}
#[test]
fn ambiguous_refused() {
    assert!(choose([50., 50.]).is_err());
    assert!(choose([f64::NAN, 50.]).is_err());
}
#[test]
fn exact_mask_only() {
    let mut doc = document();
    let r = reference();
    let paths = mask_paths(&r, &mut doc, "top", "bottom").unwrap();
    assert_eq!(paths.len(), 36);
    assert_eq!(doc["document"]["layers"][1]["mask"], r["mask"]);
    assert!(doc["document"]["layers"][0]["mask"].is_null());
    assert_eq!(doc["document"]["extra"], "preserved");
}
#[test]
fn mask_dimensions_refused() {
    let mut r = reference();
    r["width"] = json!(1280);
    assert!(mask_paths(&r, &mut document(), "top", "bottom").is_err());
}
#[test]
fn mask_schema_refused() {
    let mut r = reference();
    r["format_version"] = json!(2);
    let mut d = document();
    d["format_version"] = json!(2);
    assert!(mask_paths(&r, &mut d, "top", "bottom").is_err());
}
#[test]
fn duplicate_coords_refused() {
    let mut r = reference();
    r["mask"]["surface"]["tiles"][1] = r["mask"]["surface"]["tiles"][0].clone();
    assert!(mask_paths(&r, &mut document(), "top", "bottom").is_err());
}
#[test]
fn bad_hash_refused() {
    let mut r = reference();
    r["mask"]["surface"]["tiles"][0]["hash"] = json!("../path");
    assert!(mask_paths(&r, &mut document(), "top", "bottom").is_err());
}
#[test]
fn wrong_layer_order_refused() {
    assert!(mask_paths(&reference(), &mut document(), "bottom", "top").is_err());
}
#[test]
fn info_exact() {
    let v = json!({"width":1920,"height":1080,"layers":[{"name":"top","bounds":[0,0,1920,1080],"hasMask":true},{"name":"bottom","bounds":[0,0,1920,1080],"hasMask":false}]});
    verify(&v, "top", "bottom").unwrap();
    let mut bad = v;
    bad["layers"][1]["hasMask"] = json!(true);
    assert!(verify(&bad, "top", "bottom").is_err());
}
#[test]
fn full_unicode_fold_table() {
    let t: std::collections::BTreeMap<String, String> =
        serde_json::from_str(include_str!("casefold.json")).unwrap();
    assert_eq!(t.len(), 1557);
    assert_eq!(t["ß"], "ss");
    assert_eq!(t["ς"], "σ");
}
