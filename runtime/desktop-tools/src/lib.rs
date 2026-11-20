//! Downstream desktop policy, independent of the Session Manager core.
pub mod admin;
pub mod core;
pub mod desktop;
pub mod native;
pub mod notify;
pub mod pi;
#[cfg(test)]
mod pi_tests;
pub mod process;
pub mod startup;
pub mod state;
pub mod storage;
pub mod workspace;
pub type Result<T> = std::result::Result<T, String>;
#[cfg(test)]
mod core_tests;
#[cfg(test)]
mod notify_tests;
#[cfg(test)]
mod startup_tests;
#[cfg(test)]
mod tests;
