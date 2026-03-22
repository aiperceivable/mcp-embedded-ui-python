# Changelog

All notable changes to this project will be documented in this file.

## [0.3.1] - 2026-03-22

### Changed
- Rebrand: aipartnerup → aiperceivable

## [0.3.0] - 2026-03-11

### Added

- **Dark mode** — theme toggle button with light/dark switching, `localStorage` persistence, and system preference auto-detection (from updated shared HTML template).

### Changed

- **`allow_execute` default changed to `False`** — secure by default; callers must explicitly pass `allow_execute=True` to enable tool execution.
- README and CHANGELOG updated to reflect new default.

## [0.2.0] - 2026-03-10

### Removed

- **`/meta` endpoint** — configuration is now baked into the HTML via `{{ALLOW_EXECUTE}}` template variable.

### Added

- **ToolCallHandler 3-param support** — `handle_call(name, args, request)` is auto-detected via `inspect.signature`. Existing 2-param handlers continue to work unchanged.
- **`allow_execute`** parameter — defaults to `True`; set to `False` to disable tool execution server-side.
- **`project_name` / `project_url`** parameters — optional footer link for downstream projects (e.g., `project_name="apcore-mcp"`).
- **Package resource HTML** — `explorer.html` is now shipped as a package resource file read via `importlib.resources`, replacing the embedded Python string constant.
- **Tool search/filter, multi-content-type rendering, execution time display, cURL escaping fix** — all from updated shared HTML template.

### Changed

- `html.py` rewritten from ~430 lines to ~34 lines (reads HTML from package resource, builds project link).
- `server.py` handler detection cached at route-build time for performance.
- `pyproject.toml` updated with `force-include` for `explorer.html`.
- README updated: removed `/meta` from endpoints table, added `project_name`/`project_url` to config parameters.

## [0.1.1] - 2025-12-15

### Fixed

- Expose package version and fix `build_mcp_ui_routes` deprecation warning in tests.
- Add `auth_hook` parameter to `create_mount` with FastAPI demo example.

## [0.1.0] - 2025-12-01

### Added

- Initial implementation with Starlette routes, ASGI app factory, and mount helper.
- Tool discovery, execution, and auth hook support.
