# HuellaX · Integrated SQL-first Runbook

This is the primary runbook for the integrated launcher. It starts the live
SQL-first stack, adds the optional B/C services and the static cover, and stops
only processes that this launcher family recorded.

- Entry point: `项目主控/启动/start_huellax.sh`
- Status: `项目主控/启动/status_huellax.sh`
- Stop: `项目主控/启动/stop_huellax.sh`
- Scope: scripts and documentation only. `系统/app/`, `系统/视图工具/`, and
  `系统/数据库工具/` source code are not modified.
- The legacy AstroNova tree under `astro/` is **not** the primary system and is
  not started by this launcher. See
  [Legacy AstroNova](#10-legacy-astronova-not-the-primary-path).

---

## 1. Ports and services

| Service | Port | Required? | Started when | Health probe |
|---|---:|---|---|---|
| DB API (`spherex-db`) | **8797** | yes | always | `GET /api/health`, `ok=true` |
| MoveScope app | **8790** | yes | always | `GET /api/health`, `ok=true` |
| Sky View | **8830** | yes | always | `GET /`, HTTP 200 |
| B star catalog (`star-catalog`) | **8799** | conditional | only when `系统/数据库工具/var/star_catalog.sqlite` exists | `GET /api/v1/health`, `ok=true` |
| C AnyField (`anyfield-p1b`) | **8798** | optional | when `系统/anyfield/server.py` exists | `GET /api/v1/health`, `status=ok` |
| Static cover | **8840** | yes when a cover root exists | always with the committed fallback | `GET /`, HTTP 200, non-empty |

Core DB/app/view are started by the existing T5 launcher
(`项目主控/启动/start_all.sh`) using the same `lib.sh` PID/port/health logic.
B, C, and cover are integrated on top with their own PID files in the same
profile directory.

The browser entry point is <http://127.0.0.1:8790/>. The cover is a navigation
page, not the application.

---

## 2. Quick start

```bash
cd 项目主控/启动

./start_huellax.sh                 # production defaults: 8797/8790/8830/8799/8798/8840
./status_huellax.sh                # six-service health + SQL data snapshot
./stop_huellax.sh                  # cover → C → B → core, only owned PIDs
```

`start_huellax.sh` is idempotent: if the stack is already running under the
launcher, it reuses the recorded PIDs and exits 0 without starting duplicates.

Expected end of a successful start:

```text
SERVICE  URL                                  STATUS   PID / NOTE
DB       http://127.0.0.1:8797                ok       pid=... (launcher)
app      http://127.0.0.1:8790                ok       pid=... (launcher)
view     http://127.0.0.1:8830/               ok       pid=... (launcher)
B        http://127.0.0.1:8799                ok       pid=... (launcher)
C        http://127.0.0.1:8798                ok       pid=... (launcher)
cover    http://127.0.0.1:8840/               ok       pid=... (launcher)
```

When B or C is intentionally unavailable, their row is `skip` with a concrete
reason; B does not prevent the rest of the stack from starting. Cover is
required when enabled (the committed fallback always provides a root).

---

## 3. Sandbox ports (for tests and parallel worktrees)

Ports are explicit. The launcher never scans for a free port and never silently
changes a port. To run a completely isolated smoke test, pass all six ports:

```bash
cd 项目主控/启动

./start_huellax.sh \
  --app-port 8900 --db-port 8907 --view-port 8944 \
  --catalog-port 8949 --anyfield-port 8950 --cover-port 8945

./status_huellax.sh \
  --app-port 8900 --db-port 8907 --view-port 8944 \
  --catalog-port 8949 --anyfield-port 8950 --cover-port 8945

./stop_huellax.sh \
  --app-port 8900 --db-port 8907 --view-port 8944 \
  --catalog-port 8949 --anyfield-port 8950 --cover-port 8945
```

Rules:

- Use the **same six flags** for start/status/stop. The state file below records
  a run’s ports and refuses a different set.
- The profile is keyed by the core three ports: defaults use `run/` and
  `logs/`; non-default core ports use
  `run/sandbox-<app>-<db>-<view>/` and the matching log directory.
- The launcher exports `SPHEREX_DB_URL`, `CATALOG_URL`, and `ANYFIELD_URL` to
  the app so the app follows the selected DB/B/C ports instead of stale
  defaults.
- For a fully isolated test, change all six ports together.

Environment variables are equivalent to the flags:
`LAUNCH_APP_PORT`, `LAUNCH_DB_PORT`, `LAUNCH_VIEW_PORT`,
`LAUNCH_CATALOG_PORT`, `LAUNCH_ANYFIELD_PORT`, `LAUNCH_COVER_PORT`.
If both are set, command-line flags win.

---

## 4. SQL data sources (primary)

The SQL databases are the source of truth. Nothing in `astro/` is consulted for
live answers.

| Data | Path | Role |
|---|---|---|
| SPHEREx catalog | `系统/数据库工具/var/catalog.sqlite` | targets, frames, observations, weeks, epochs, cutouts, blobs, coverage, provenance. Served read-only by DB API 8797. Tracked in git. |
| Star catalog | `系统/数据库工具/var/star_catalog.sqlite` | separate SQLite for Gaia/2MASS/WISE field caches and matches. Served by B 8799. Gitignored and rebuildable. |
| App exports/cache | `系统/app/data/` | derived exports and local pixel/cache material used by MoveScope. Not a second catalog. |
| View static data | `系统/视图工具/data/` | static presentation data for Sky View. Not an authority for observations. |

Important semantics:

- MoveScope queries the DB API for arbitrary-coordinate epoch resolution. The
  launcher points it at the managed DB port.
- B is a separate SQLite database on a separate port. It does not mutate the
  SPHEREx catalog.
- The cover is static navigation only; it makes no SQL queries.
- `catalog.sqlite` and `star_catalog.sqlite` must not be silently substituted
  for each other, and missing data must remain an explicit failure/`skip`, not
  an invented empty result.

---

## 5. Data import prerequisites

### 5.1 SPHEREx catalog (required)

`系统/数据库工具/var/catalog.sqlite` is committed with the repository. If it is
missing or you need to rebuild it:

```bash
cd 系统/数据库工具
PYTHON=/Users/yiao/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/python/bin/python3 \
  ./tools/import_all.sh
# or minimal empty schema:
PYTHON=... ./cli.py init
```

The launcher refuses to start rather than starting the DB against a missing
database. See `项目主控/启动/README.md` for the underlying T5 behavior.

### 5.2 Star catalog for B (conditional)

B starts only when the file below exists:

```text
系统/数据库工具/var/star_catalog.sqlite
```

It is ignored by git and is not part of a fresh checkout. To seed it from an
existing integration checkout, copy the file read-only:

```bash
cp /path/to/existing/系统/数据库工具/var/star_catalog.sqlite \
   系统/数据库工具/var/star_catalog.sqlite
```

Or rebuild it with the catalog tools (for example
`系统/数据库工具/tools/import_gaia.py`). If the file is absent, the launcher
prints `B 8799 skipped — star_catalog.sqlite not found: ...` and continues with
the required services. Use `--no-catalog` to skip B explicitly even when the
file exists.

Do **not** commit `star_catalog.sqlite`; it is a runtime artifact.

### 5.3 C AnyField (optional)

C starts when `系统/anyfield/server.py` exists. It is best-effort by default:
if the port is occupied or C fails its health probe, the launcher stops only the
C instance it started, prints a warning, and continues. Use
`--require-anyfield` to make C mandatory.

### 5.4 Python

DB and B need only the standard library. MoveScope needs `numpy` and `Pillow`;
the launcher auto-detects the workspace Python and accepts an explicit override:

```bash
PYTHON=/path/to/python3 ./start_huellax.sh
```

C is started through `系统/anyfield/start.sh` with the same interpreter. Cover
and Sky View use the `python3` on `PATH` for `python3 -m http.server`.

---

## 6. Cover on 8840

The cover is served with the standard library:

```bash
cd <cover-root> && python3 -m http.server 8840 --bind 127.0.0.1
```

The launcher resolves the cover root in this order:

1. `--cover-dir <dir>` or `HUELLAX_COVER_DIR` (must contain `index.html`);
2. `<repo>/cover/` — the expected new static cover from the cover branch;
3. `<repo>/portada/`;
4. `<repo>/封面/`;
5. committed fallback: `项目主控/启动/cover/`.

The fallback page is intentionally minimal and is replaced automatically when a
project-level `cover/index.html` exists. The cover branch owns
`INTEGRATION.md`; this runbook (`HUELLAX.md`) is the launcher documentation and
does not modify `INTEGRATION.md`.

The cover root is printed at startup and in `status_huellax.sh`. If an explicit
`--cover-dir` is invalid, start fails clearly; if no root is found at all,
cover is skipped with a reason.

---

## 7. Logs, PIDs, state, and safety

```text
项目主控/启动/
  start_huellax.sh      integrated start
  stop_huellax.sh       integrated stop
  status_huellax.sh     read-only status
  huellax_lib.sh        integrated helpers on top of lib.sh
  lib.sh                shared T5 PID/port/health/stop primitives
  probe.py              Python stdlib health/SQLite probe
  cover/index.html      committed fallback cover
  logs/<profile>/       per-service logs: db, app, view, catalog, anyfield, cover
  run/<profile>/        PID files + huellax.state
```

| Profile | Example paths |
|---|---|
| default (8790/8797/8830) | `run/{db,app,view}.pid`, `run/{catalog,anyfield,cover}.pid`, `run/huellax.state` |
| sandbox (`8900/8907/8944`) | `run/sandbox-8900-8907-8944/...`, `logs/sandbox-8900-8907-8944/...` |

Safety properties:

- The launcher only signals PIDs recorded in its own PID files and only after
  verifying the command line contains the expected service marker.
- A PID file pointing at a foreign process is **not** killed; stop refuses,
  preserves the PID file, and exits non-zero.
- Foreign listeners on a required port are reported with PID and command line;
  start refuses rather than killing them or silently shifting ports.
- `stop_huellax.sh` stops extra services first, then core only when
  `huellax.state` records `core_owned=1`. If core was started manually with
  `start_all.sh`, it is left running and the script prints the explicit
  `stop_all.sh` command instead.
- No `pkill -f python`, no Docker, no system service, no nginx.

`run/huellax.state` is a small key/value file:

```text
format=1
started_at=...
profile=...
flags=--app-port ... --db-port ... --view-port ... --catalog-port ... --anyfield-port ... --cover-port ...
ports=...
core_owned=1
catalog=1
anyfield=1
cover=1
cover_dir=...
git=...
```

It is used to stop core safely and to reject start/stop with a different port
set. Runtime `run/` and `logs/` are ignored by git.

---

## 8. Stop, restart, and reset

### Normal stop

```bash
cd 项目主控/启动
./stop_huellax.sh
```

Stop order is **cover → C → B → core (view → app → DB)**. After stopping, the
script prints every managed port as released or reports a foreign listener that
it deliberately did not touch.

### Stop only the core three

The T5 scripts remain available and manage only DB/app/view:

```bash
./stop_all.sh
./status.sh
```

### Reset runtime state

With the stack stopped, `项目主控/启动/run/` and `项目主控/启动/logs/` are safe to
delete; they contain PIDs, the integration state file, and logs. Do not delete
`系统/数据库工具/var/catalog.sqlite` as a “reset” unless you intend to rebuild
the catalog.

### Reset data (explicit, destructive)

- Rebuild the SPHEREx catalog with `系统/数据库工具/tools/import_all.sh`
  (it regenerates `var/catalog.sqlite` and exports).
- The star catalog is rebuildable: delete
  `系统/数据库工具/var/star_catalog.sqlite` and re-import Gaia/2MASS/WISE
  fields. B will then be skipped until the file is recreated.
- Back up any local catalog before deleting it. The launcher itself never
  deletes a database.

### Restart

```bash
./stop_huellax.sh && ./start_huellax.sh
```

Use the same port flags for both commands.

---

## 9. Troubleshooting

| Symptom | Meaning | Action |
|---|---|---|
| `core service ... is held by a foreign process` | Something else listens on 8790/8797/8830 (or sandbox port). | Inspect the printed PID/command. Stop it yourself, or use a complete set of six sandbox ports. The launcher will not kill it. |
| `B 8799 skipped — star_catalog.sqlite not found` | The separate star catalog is absent. | Seed `系统/数据库工具/var/star_catalog.sqlite` (§5.2) or accept the skip. Do not pass the SPHEREx catalog as B. |
| `C 8798 ... skipped` | Optional C is unavailable, its port is busy, or its health failed. | Fix the port/DB and retry; use `--require-anyfield` if C must be mandatory. Foreign processes are left untouched. |
| `cover ... skipped` / 404 | No cover root with `index.html`, or an explicit root is wrong. | Create `<repo>/cover/index.html`, pass `--cover-dir`, or rely on the committed fallback. |
| `missing SQLite catalog` | `系统/数据库工具/var/catalog.sqlite` is absent. | Run `tools/import_all.sh` or `cli.py init` (§5.1). |
| `numpy`/`Pillow` import error | Wrong Python for MoveScope. | Set `PYTHON` to the workspace interpreter with numpy/Pillow. |
| `state file ports differ` | A previous integrated run used another port set. | Run `stop_huellax.sh <recorded flags>`, then start with the new set. |
| `PID ... command line does not match` | PID reuse or a foreign process in a launcher PID file. | Confirm the PID; the launcher intentionally refuses to stop it. Delete the stale PID file only after confirming no managed service is using it. |
| `stop` leaves core running | Core was started outside the integrated launcher (`core_owned=0`). | Run `./stop_all.sh` explicitly, or start/stop the whole stack through the integrated scripts. |
| status shows `FAIL` with connection refused | That service is not running. | Start it with the same six flags; check the service log under `logs/<profile>/`. |

---

## 10. Legacy AstroNova (not the primary path)

`astro/` is the legacy AstroNova/upstream material (static data, pages, its own
contracts). The integrated launcher and the primary runbook do **not** start it,
read it, or treat its static JSON as authoritative.

| Aspect | Legacy AstroNova (`astro/`) | Integrated SQL-first stack |
|---|---|---|
| Primary data | bundled/static files in the legacy tree | `系统/数据库工具/var/catalog.sqlite` served by DB API 8797 |
| Live entry point | legacy static pages | MoveScope on 8790 |
| Star data | not the primary star source | separate `var/star_catalog.sqlite` served by B 8799 |
| Updates | whatever was copied into the tree | explicit import/ingest with schema version and provenance |
| Launched by | not launched by `start_huellax.sh` | DB, app, view, B, C, cover managed by this launcher |
| Authority | reference/legacy only | source of truth for product queries |

- SQL catalog + DB API is the primary data plane.
- MoveScope is the single product entry point.
- Sky View (8830) is an optional static companion.
- The cover (8840) is navigation only.
- Any offline/static material under `astro/` remains a legacy reference unless a
  future task explicitly re-integrates it. Do not copy AstroNova static data into
  the SQL catalog or into MoveScope as a substitute for a DB query.

---

## 11. Verification (smoke evidence)

The integrated launcher was smoke-tested without touching the production ports.
Representative run (all six ports sandboxed):

```bash
./start_huellax.sh --app-port 8900 --db-port 8907 --view-port 8944 \
  --catalog-port 8949 --anyfield-port 8950 --cover-port 8945
./status_huellax.sh --app-port 8900 --db-port 8907 --view-port 8944 \
  --catalog-port 8949 --anyfield-port 8950 --cover-port 8945
./stop_huellax.sh --app-port 8900 --db-port 8907 --view-port 8944 \
  --catalog-port 8949 --anyfield-port 8950 --cover-port 8945
```

Verified behavior:

- 6/6 health (`DB`, `app`, `view`, `B`, `C`, `cover`) in one start; exit 0.
- App custom-coordinate request used the managed sandbox DB:
  `GET /api/epochs?ra=269.452077&dec=4.693365&fov=0.25` returned
  `matched_target_id=barnard` and `coverage_level=C2`.
- Repeated start reused all PIDs (no duplicate processes), exit 0.
- Stop released all six ports, removed PID/state files, exit 0.
- A foreign process on the cover port was reported by PID/command, start exited
  1, core ports stayed free, and the foreign process remained alive.
- A foreign PID planted in `cover.pid` was refused and preserved by stop (exit
  1); the foreign process stayed alive.
- A simulated cover startup failure rolled back only the services started by
  that run and released all six ports.
- With `--no-catalog`, B was explicitly skipped; with the star DB temporarily
  absent, B was skipped automatically; the rest of the stack stayed healthy.
- A project-level `cover/index.html` was served preferentially over the
  fallback when present.

Production ports 8790/8797/8830/8799/8798/8840 were not left running during
these tests.

---

## 12. Limitations

- No daemon/supervisor, Docker, nginx, launchd/systemd, or reverse proxy.
- Localhost only; no authentication or HTTPS termination.
- No automatic port scanning or shifting; port conflicts are explicit failures.
- The fallback cover is a placeholder; a project-level `cover/` from the cover
  branch replaces it at resolution time.
- B’s star catalog is a set of cached fields, not a full-sky service. Missing
  fields are explicit partial/unavailable responses, not “no source”.
- C is optional and may be skipped; MoveScope must degrade explicitly when B or
  C is absent.
- The launcher reports foreign processes but never takes ownership of them.
