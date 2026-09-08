# gpui-agentic-http

A local-only HTTP surface for driving and inspecting a gpui app without a
human at the keyboard: open a screen, click a button, read back what's on
screen -- as actions an agent calls over HTTP, not OS-level GUI automation.

Extracted from sgerp-admin's own `debug_http.rs`
(`~/dev/sgerp-rust/desktop/crates/admin/src/agentic_http.rs`), which is
still the reference consumer. See `docs/2026-09-06-gpui-agentic-http-design.md`
in that repo for the full design history.

## What this crate provides

- `Action`/`Param`/`ParamLocation`: a small, serializable description of
  one HTTP-callable capability.
- `ModuleRegistration<T>`: one app module's own action list plus its
  dispatch function, prefixed so two modules never collide.
- `AgenticServer<T>`: binds a port, runs the accept-loop thread, bridges
  each request across to your app's own foreground thread via a one-shot
  channel, and answers `GET /` with every registered module's actions
  merged into one self-describing list (plus an `"app"` field naming your
  app).
- A registry-drift-test helper: fails a test, not a silent 404, when an
  action is documented but not routed or the reverse.
- `scripts/agentic_mcp_server.py`: an MCP server over stdio that turns
  `GET /`'s own live registry into MCP tools -- no hardcoded tool list on
  the Python side, ever.
- `skills/agentic-app/SKILL.md`: a bootstrap Claude Code skill. Its entire
  content is "scan the shared port range, `GET /` what you find, use what
  it says" -- never a hardcoded action list.

## Using it

Add as a path dependency during development:

```toml
gpui-agentic-http = { path = "../../../gpui-agentic-http" }
```

See sgerp-admin's own `agentic_http.rs` for a complete, real consumer.
