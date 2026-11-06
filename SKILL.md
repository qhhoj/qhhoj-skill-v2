---
name: qhhoj-skill-v2
description: "Operates the QHHOJ v2 online-judge site (qhhoj.com; Vue SPA frontend + NestJS /api/internal backend, repos qhhoj/frontend-v2 and qhhoj/backend-v2) through the browser or the same-origin JSON API using the user's session: sign in with 2FA/password gates, create and edit problems, upload test archives, checker/grader files, PDF statements, materials and images, import Polygon packages (ZIP upload or linked import/sync), create and run contests site-wide or inside a chosen organization, manage organization members/requests/tags/quota, submit solutions and read verdicts, rejudge/rescore, write blog posts, and file tickets — each only as far as the account's permissions, field gates and quotas allow. Use when asked to create/upload/fix a problem or test data, create or configure a contest, pick the owning organization, submit code, or perform any judge-operation on qhhoj.com with the user's account."
compatibility: "Needs network access to the site, a browser session or an HTTP client that carries the qhhoj_session cookie, and Python 3 (stdlib only) for scripts/lookup_contract.py"
metadata:
  version: "2.0.0"
  source-backend: "github.com/qhhoj/backend-v2 @ 867fd75"
  source-frontend: "github.com/qhhoj/frontend-v2 @ 85e4fe9"
---
# qhhoj-skill-v2 — operating the QHHOJ v2 judge site

Drive `https://qhhoj.com` (or another deployment of the same code) with the user's own account: author problems, upload test data, import Polygon packages, build contests in the right organization, submit and judge solutions — nothing beyond what the account may do and the user asked for.

Two equal channels, one session: the Vue SPA at the routes in [workflows.md](references/workflows.md), and the JSON API under `/api/internal` indexed in [api.md](references/api.md). Prefer the UI to explore and verify; prefer the API for exact writes. The skill is tool-agnostic: use whatever browser automation or HTTP client you have. If you have neither, or the session is not authorized, prepare the exact request/URL and report the limitation — never claim an action succeeded without observing it.

Not the legacy stack: the older skill at `github.com/qhhoj/qhhoj-skill` (name `qhhoj`) drives the Django/DMOJ fork `qhhoj/online-judge` (form POSTs, `csrfmiddlewaretoken`, `/api/v2`). This skill is for the **v2** stack (`frontend-v2` + `backend-v2`, JSON `/api/internal`) and none of those mechanics apply. Tell them apart by the login page: v2 is a Vue SPA calling `/api/internal/auth/login`; the legacy one renders Django's `/accounts/login/`.

## Quick start (HTTP client)

`scripts/qhhoj_client.py` wraps the whole API — session + CSRF, paged lists, org-scoped creates, data upload, contest assembly, submissions, Polygon jobs:

```python
import sys; sys.path.insert(0, '<skill_dir>/scripts')
from qhhoj_client import QhhojClient, case

c = QhhojClient('https://qhhoj.com', 'user', 'pass')   # totp_secret='JBSW…' if 2FA; or api_token='…'
c.login()                                              # raises QhhojError with the backend's code
meta = c.problem_meta()                                # catalog ids for group/type/language
orgs = c.creation_organizations('problem')             # where this account may create
c.create_problem(code='demo_aplusb', name='A + B', time_limit=2, memory_limit=262144,
                 points=1000, type_ids=[type_id], group_id=group_id,
                 organization='myorg', description='Compute $A+B$.')
c.upload_archive('demo_aplusb', 'tests.zip')           # zip of .in/.ans files
c.put_data('demo_aplusb', cases=[case('C', '1.in', '1.ans', 100)])   # full replace
c.create_contest(key='demo', name='Demo Contest',
                 start='2026-11-07T09:00:00+07:00', end='2026-11-07T12:00:00+07:00',
                 organization='myorg')
c.set_contest_problems('demo', [(c.problem_id('demo_aplusb'), 100)])  # ids, not codes
sid = c.submit('demo_aplusb', 'print(int(input()) + int(input()))')   # language key auto-resolves
print(c.wait_for_verdict(sid))
```

CLI probe (read-only after login): `python3 scripts/qhhoj_client.py https://qhhoj.com user pass [--totp S]` prints the session, capabilities, creation organizations and a contest sample. Needs Python 3 + `requests`.

## Operating loop

1. **Classify the request.** A "bài" is a *problem* (create manually / import package / upload tests / Polygon), a *submission* (code to judge), or a *blog post* (API is `/posts`, not `/blog`). "Tạo contest" → which organization owns it? Ambiguous scope → ask before writing.
2. **Read the session.** `GET /api/internal/auth/me` (or the UI). Check: signed in? `twoFactorRequired` / `passwordChangeRequired` gates (finish them via their flows — a partial session is not signed in)? `impersonatorId` set (mention it in reports)? Record `user.permissions` and `adminCapabilities`. Details: [permissions.md](references/permissions.md).
3. **Check rights before acting.** Map the action → permission codename / per-object relation / field gate / quota in [permissions.md](references/permissions.md). There is no "what can I do" endpoint: derive from `permissions` + `adminCapabilities` + GET access to the object. Never probe with mutations, and never widen scope to bypass a refusal.
4. **Choose the owning organization deliberately.** `GET /api/internal/organizations?canCreate=problem` (or `contest`), all pages. If the user named an org, use exactly that slug (missing from the list → report "no rights", don't substitute). If unset and the choice changes visibility or quota → ask. Don't accept a form's default silently.
5. **Open the right page / call the right endpoint.** Follow [workflows.md](references/workflows.md). Before any API write, resolve the exact contract: `python3 scripts/lookup_contract.py METHOD /path` (relative to this skill's directory; `list <word>` finds operations). The operation's embedded description states permissions, quotas and error codes — read it, don't guess field names, enums, ids or methods.
6. **Send minimal diffs.** PATCH only changed fields; PUT `/problems/{code}/data` is a full replace (resend every case to keep). Never echo a GET response back as a request body. Multipart: exactly the documented field(s); repeated query keys for arrays (`typeIds=a&typeIds=b`), never `typeIds[]`.
7. **Verify by reading back.** GET the object / reload the page: code, owner org, visibility, statement, `feedback`, job state. Async work (imports, packages, PDFs, rescores) returns 202 + id — poll the **GET** until a terminal state or report it as still running. After a timeout, look for the object/job before retrying so nothing is created twice.
8. **Report** the object URL, what changed, owning org, visibility, job ids, and anything blocked — quoting the backend's own `error.code`/`issues`. Keep credentials, cookies, CSRF tokens and unreleased problem content out of logs and reports.

## Core mechanics (memorize)

- **Base & auth**: everything is same-origin under `/api/internal`, cookie `qhhoj_session`, `credentials: same-origin`. Sign in: `POST /auth/login {username, password}` → returns `csrfToken`; API-token sessions exist but have `csrfToken: null`.
- **CSRF**: send header `X-CSRF-Token` on every non-GET from a cookie session. On `csrf_failed`: re-`GET /auth/me` and resend once.
- **Envelope**: objects `{data: …}`, lists `{data: […], meta: …}` (page from 1), 204 → no body. File downloads and raw YAML/PDF bypass the envelope. Failures: `{error: {code, message, fields?, issues?}}` (+`Retry-After` on 429/503).
- **Units & formats**: `timeLimit` seconds (float, 0.01–60; > 5 needs a permission), `memoryLimit` **KiB**, problem `points` 800–3500, datetimes ISO-8601 with explicit offset. Problem `code`/contest `key` `^[a-z0-9_]{1,32}$` (problem codes also avoid reserved `deleted|meta|imports|random`; contest key ≠ `current`). Org problem codes extend the org prefix = slug's `[a-z0-9]` (≤ 23 chars) + `_`.
- **Async jobs**: Polygon imports/syncs answer 202 `{jobId}` → poll `GET /problems/imports/{jobId}` (states `waiting/active/delayed/prioritized/completed/failed`); problem packages 200/202 `building` → poll GET; contest data/export similar. Polling is free; re-submitting is not.
- **Budgets**: uploads 30/h (shared), imports 10/h, submissions 20/min + 2 unfinished, blog 10/h, deletes 10/h. Respect `Retry-After`.

## Choosing documents

| Need | File |
| --- | --- |
| Who may do what; field gates; quotas; error playbook | [references/permissions.md](references/permissions.md) |
| Step-by-step UI routes and recipes (problem → data → contest → org → submit → blog) | [references/workflows.md](references/workflows.md) |
| Endpoint index (231 operations) | [references/api.md](references/api.md) |
| Exact request/response schemas for one operation | `python3 scripts/lookup_contract.py` over [references/contracts.json](references/contracts.json) |
| Where each fact came from; how to refresh the snapshot | [references/sources.md](references/sources.md) |
| A ready HTTP client (login/2FA, creates, uploads, submits, job polling) | [scripts/qhhoj_client.py](scripts/qhhoj_client.py) — docstring is the full reference |

## Hard rules

- Stay inside the request: holding a permission (publish, announce, rejudge, delete, rating, scope change) is not authorization to use it.
- Never: probe permissions with writes, bypass 403/404 by URL-crafting, self-escalate, impersonate, resubmit others' work, or pick a different org than requested to dodge quota/prefix.
- The repos describe the deployed code, not a promise about production: if live behavior differs from the snapshot, trust the live response, adjust, and note the drift for [references/sources.md](references/sources.md).
