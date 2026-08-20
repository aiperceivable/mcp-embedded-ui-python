# Changelog

All notable changes to this project will be documented in this file.

## [0.5.0] - 2026-08-20

### Changed

- **BREAKING (spec F6/FR-1): the Try-It editor prefill no longer fabricates values.**
  Synced `explorer.html` from the spec repo at 0.5.0. The prefill now emits exactly
  the keys listed in `inputSchema.required`, using each property's declared
  `default` when it has one and `null` otherwise. Optional properties are omitted
  entirely, generation does not recurse into nested objects, and a schema with no
  `required` prefills `{}`.

  The previous rule invented a type-based value for *every* property
  (`"string"` → `""`, `"number"` → `0`, …), which had two consequences. First,
  size: a 257-property schema produced a 259-line prefill inside a 120px editor.
  Second, and more seriously, it emitted a key for every property and drew every
  value from the declared type, so it satisfied `required` and the type
  constraints unconditionally — making the 0.4.0 Validate button incapable of
  failing on a fresh prefill for any schema. `null` supplies the key without
  asserting a value and is rejected wherever the schema does not admit it.

### Fixed

- **`project_url` is now scheme-checked before being placed in `href`.** Only
  `http://`, `https://`, `mailto:` and a leading `/` are accepted; anything else
  renders the project name as plain text. TAB/LF/CR are stripped and the value
  trimmed before the check, because browsers ignore those while resolving a
  scheme. Not an exploitable vulnerability — `project_url` is deployment
  configuration, not caller input — but HTML escaping alone never stopped
  `javascript:`.

- **`/validate` no longer mishandles a tool whose `inputSchema` cannot be
  compiled.** Such a schema is now reported as a single `keyword: "schema"`
  validation failure at HTTP 200, per the new F7 contract.
  Previously the uncaught validator error surfaced as a 500.
- **`CallResult._meta` is now declared optional.** It was a required key on a
  `total=True` TypedDict, while every payload this package emits omits `_meta`
  when the handler supplies no trace id (PROTOCOL.md). TypeScript and Rust
  already declared it optional; Python was the outlier, contradicting the spec,
  its own wire format, and both sibling SDKs.
- An explicit `default: null` in a schema is now honoured. The previous guard
  (`props[key]['default'] != null`) discarded it and fell through to a fabricated
  type default.

### Added

- **`ValidateResult` and `ValidationFailure` exported from the package root**
  (F7). The `/validate` response shapes are protocol, so callers can now name
  what the endpoint returns. Declared as base + `total=False` TypedDicts to stay
  valid on Python 3.10, where `typing.NotRequired` does not exist.

### Tests

- Added template guards for FR-1: the prefill must read `inputSchema.required`
  and must not fabricate type-based values. These run even when the spec repo is
  not checked out alongside, unlike the existing drift check.
- Added `TestCallResultShape` (declared shape matches the emitted payload) and a
  `/validate` case for an uncompilable schema.
- **`pytest` now sets `pythonpath = ["src"]`.** Without it an outdated
  `pip install .` in the environment shadows `src/`, so the suite imported the
  installed copy and reported green against code that was not the working tree.

## [0.4.0] - 2026-04-28

### Added

- **`POST /tools/{name}/validate` endpoint** — implements F7 from the spec. Validates request args against the tool's `inputSchema` without invoking the handler, returns `{"valid": true}` or `{"valid": false, "errors": [...]}`. Not gated by `allow_execute` or `auth_hook` (per F7 spec). Adds `jsonschema>=4.0.0` dependency.
- **`explorer.html`** — synced from spec repo; gains the Validate button next to Execute.

## [0.3.1] - 2026-03-26

### Changed

- Update `explorer.html` — sync cross-language implementation links from relative paths to absolute GitHub URLs.

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
