# Security model

## Scope

Big Cycle Atlas v1.0 is a **single-operator research application** — no
authentication, no multi-tenancy, no per-user data. The intended exposure
is loopback only.

## What is in place

- **Loopback binding**: API serves on `127.0.0.1` (BCA_HOST/BCA_PORT
  overridable, loopback by default); compose web port binds `127.0.0.1`.
- **Same-origin production**: the API serves the built frontend, so the
  browser issues same-origin requests — no cross-origin surface by default.
- **CORS**: restricted to configured origins (`localhost:3000` dev default)
  and explicit methods only (GET/POST/DELETE). Cross-site forms cannot
  call JSON mutation endpoints (preflight required).
- **SQL**: all access via SQLAlchemy ORM/parameters — no interpolated
  query strings.
- **Static serving**: Starlette StaticFiles resolves paths inside the
  dist directory (traversal attempts return 404).
- **Secrets**: none in the repo — `apps/api/.env` is gitignored;
  `.env.example` carries placeholders only.
- **Stop safety**: `Stop.bat` verifies each recorded PID's command line
  contains the repo path before terminating — it cannot kill unrelated
  python/node processes.
- **Dependency audits**: `npm audit` and `pip-audit` clean at release.

## Browser risk notes (even same-origin)

- No CSRF tokens on mutation endpoints. JSON POSTs from foreign origins are
  blocked by CORS preflight, but the API has no auth — any process on your
  machine (or a page if you deliberately expose the port) can call it.
- LocalStorage prefs/workspace data is unencrypted browser storage —
  normal for this class of app; don't store secrets in widget config.
- `/api/*` error responses are JSON; the app surface does not reflect
  unsanitized HTML (React escapes by default).

## Hardening for private-network exposure

Never bind `0.0.0.0` directly. Put an authenticating reverse proxy in
front (nginx sample `deploy/linux/nginx-bca.conf`, or Caddy/Authelia),
terminate TLS there, and keep the app on loopback upstream.

## Audit log (v1.0.0-rc.1)

- npm audit: 0 vulnerabilities | pip-audit: 0 vulnerabilities
- Secrets scan: no tracked `.env`; `.gitignore` covers `backups/`, `.run/`
- Mutation endpoints reviewed: portfolio (row-locked), watchlist,
  strategy simulate — all validated via Pydantic/ORM
- Remaining accepted risks: no auth, no rate limiting, single-user model
