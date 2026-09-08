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
- `src/bin/agentic_mcp_server.rs`: an MCP server over stdio that turns
  `GET /`'s own live registry into MCP tools -- no hardcoded tool list,
  ever. (An earlier Python prototype did the same job; rewritten in Rust
  so a Rust consumer never has to shell out to a second language runtime
  just to talk to itself.)
- `skills/agentic-app/SKILL.md`: a bootstrap Claude Code skill. Its entire
  content is "scan the shared port range, `GET /` what you find, use what
  it says" -- never a hardcoded action list.

## What ships in this repo

- `src/`: the Rust library crate (`Action`/`Param`/`ParamLocation`,
  `ModuleRegistration<T>`, `AgenticServer<T>`, the registry-drift-test
  helper) plus `src/bin/agentic_mcp_server.rs`, a second binary target in
  the same crate -- the MCP bridge. `cargo build --release` produces both;
  see `.mcp.json.example` for how a consumer wires the binary in.
- `skills/agentic-app/SKILL.md`: the bootstrap Claude Code skill. Copy or
  symlink into a consuming project's own `.claude/skills/agentic-app/`.

## Using it

Add as a dependency:

```toml
gpui-agentic-http = { git = "https://github.com/emakarov/gpui-agentic-http", rev = "<commit>" }
```

or, during local development on this crate itself, as a path dependency
(must be an **absolute** path -- a relative one breaks as soon as a
consumer is checked out at a different depth, e.g. a plain checkout vs. a
`.claude/worktrees/*` worktree):

```toml
gpui-agentic-http = { path = "/absolute/path/to/gpui-agentic-http" }
```

See sgerp-admin's own `agentic_http.rs` for a complete, real consumer.

**Gotcha:** an `Action`'s own `path` must NOT repeat its module's
`prefix` -- `AgenticServer` prepends the prefix itself when routing and
when building `GET /`'s response. A module registered with
`prefix: "map"` declares `path: "/state"`, not `path: "/map/state"`; the
latter double-prefixes to `/map/map/state` and only becomes obvious once
you read the routing code that builds it.
