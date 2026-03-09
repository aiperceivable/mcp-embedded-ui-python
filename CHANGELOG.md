# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/).

## [0.1.0] - 2026-03-09

### Added

- Core ASGI route builder (`build_ui_routes`) with 5 endpoints:
  - `GET /` — self-contained HTML explorer page
  - `GET /meta` — JSON config (`allow_execute`, `title`)
  - `GET /tools` — tool summary list
  - `GET /tools/{name}` — tool detail with input schema
  - `POST /tools/{name}/call` — tool execution
- High-level factories: `create_app()` (standalone ASGI) and `create_mount()` (Starlette/FastAPI prefix mount)
- Dynamic tools support — static list, sync callable, or async callable
- Auth hook — sync and async context manager patterns
- Configurable title with XSS-safe HTML escaping
- `annotations` field omitted (not `null`) when absent
- `_meta` with `_trace_id` omitted when trace ID is empty
- `allow_execute=False` blocks at handler level, not just UI
- Auth error responses return only `{"error": "Unauthorized"}` — no detail leaking
- Backward-compatible `build_mcp_ui_routes()` alias with `DeprecationWarning`
- 42 tests covering all endpoints, auth, dynamic tools, security, and exports
