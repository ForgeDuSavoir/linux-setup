//! Optional request guard for SUPER+Tab; ordinary menu/browser behavior is unchanged.
use crate::Result;
#[derive(Debug, Clone)]
pub struct Expected {
    pub workspace: i64,
    pub owner: String,
}
impl Expected {
    pub fn parse(id: &str, owner: &str) -> Result<Self> {
        let workspace = id
            .parse::<i64>()
            .map_err(|_| "invalid expected workspace")?;
        let uuid = owner.len() == 36
            && owner.bytes().enumerate().all(|(i, c)| {
                if [8, 13, 18, 23].contains(&i) {
                    c == b'-'
                } else {
                    c.is_ascii_digit() || (b'a'..=b'f').contains(&c)
                }
            });
        if !(1..=2_147_483_646).contains(&workspace) || !(owner == "neutral" || uuid) {
            return Err("invalid expected workspace/owner".into());
        }
        Ok(Self {
            workspace,
            owner: owner.into(),
        })
    }
    pub fn check(&self, workspace: i64, owner: &str, special: &str) -> Result<()> {
        if self.workspace != workspace || self.owner != owner || !special.is_empty() {
            return Err("expected workspace/context changed; launcher cancelled".into());
        }
        Ok(())
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn validates() {
        for id in ["0", "-1", "2147483647", "oops"] {
            assert!(Expected::parse(id, "neutral").is_err());
        }
        assert!(Expected::parse("4", "A").is_err());
        assert!(Expected::parse("4", "11111111-1111-1111-1111-111111111111").is_ok());
    }
    #[test]
    fn exact_target() {
        let e = Expected::parse("5", "neutral").unwrap();
        assert!(e.check(5, "neutral", "").is_ok());
        for (w, o, s) in [
            (6, "neutral", ""),
            (5, "other", ""),
            (5, "neutral", "special:global"),
        ] {
            assert!(e.check(w, o, s).is_err());
        }
    }
}
