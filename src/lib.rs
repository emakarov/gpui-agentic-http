//! `gpui-agentic-http`: a local-only HTTP surface for driving and
//! inspecting a gpui app without a human at the keyboard. See this crate's
//! own `README.md` for the full design rationale, ported from
//! sgerp-admin's `debug_http.rs` (`~/dev/sgerp-rust`).

mod registry;
mod server;

pub use registry::{assert_registry_routable, Action, ModuleRegistration, Param, ParamLocation};
pub use server::{parse_query_string, AgenticCall, AgenticServer};
