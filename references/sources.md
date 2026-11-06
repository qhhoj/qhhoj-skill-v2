# Provenance and maintenance

## Snapshot basis

Written on 2026-11-06 from source, without logging into or mutating any real account:

- frontend [qhhoj/frontend-v2](https://github.com/qhhoj/frontend-v2) @ `85e4fe984a2b0bd563c42de71220e1777a04439b` — routes, admin screens/access, creation-owner flow, API client conventions, submit flow.
- backend [qhhoj/backend-v2](https://github.com/qhhoj/backend-v2) @ `867fd75712a8e03e972fce9d2de7f445dc30b487` — controllers, DTOs, access policies, constants; `openapi.json` at the repo root is the contract source.
- The backend `openapi.json` and the frontend-generated `src/api/generated/openapi.json` were compared at these commits: identical (294 paths / 497 schemas), so `references/contracts.json` regenerated from the backend file is the frontend's contract too.

## Where each fact lives

`references/contracts.json` — machine truth. Built by keeping the OpenAPI operations whose tags are Auth, Blog, Contest editing, Contests, Organizations, Problem editing, Problems, Submissions, plus the user-facing Judging ops on `/submissions` and the Tickets ops, with every transitively referenced schema. Excluded (out of operator scope, do not guess their contracts): `admin/*` system endpoints, similarity checks, external-judge status, canned replies, sync/integration API, notifications, users, comments, search, live events.

`references/api.md` — generated 1:1 from `contracts.json` paths (method, path, summary). Regenerate together with it.

`references/permissions.md` — backend sources: `libs/auth/src/principal/permissions.ts` (catalog), `apps/api/src/modules/auth/core/dto/session.response.ts` + `session-responses.service.ts` (session & capabilities), `libs/auth/src/guards/auth.guard.ts` (CSRF), `libs/problems/src/problem-access.ts`, `apps/api/src/modules/problems/editing/` (DTO + gates), `apps/api/src/modules/contests/` (`contest-access.ts`, `contest-edit-rules.ts`), `apps/api/src/modules/organizations/core/organization-access.ts`, `libs/community/src/organizations.ts` (prefix), `apps/api/src/modules/*/rate-limits.ts` and per-module constants.

`references/workflows.md` — frontend sources: `src/router/routes.ts`, `src/features/admin/admin-routes.ts` + `admin-screens.ts` + `admin-access.ts`, `src/features/admin/creation/creation-owners.ts` + `creation-scope.ts` + `CreationOwnerPicker.vue`, `src/api/client.ts`, `src/api/submissions.api.ts`, `src/api/blog.api.ts`; plus the backend descriptions above for every API step.

## Refreshing the snapshot

```bash
git clone --depth 1 https://github.com/qhhoj/backend-v2 /tmp/backend-v2
python3 - <<'EOF'
import json
spec = json.load(open('/tmp/backend-v2/openapi.json'))
KEEP_TAGS = {'Auth','Blog','Contest editing','Contests','Organizations','Problem editing','Problems','Submissions'}
EXTRA = {('POST','/api/internal/submissions/rejudge'),('POST','/api/internal/submissions/rescore'),
 ('GET','/api/internal/submissions/batches/recent'),('POST','/api/internal/submissions/{id}/abort'),
 ('POST','/api/internal/submissions/{id}/lock'),('DELETE','/api/internal/submissions/{id}/lock'),
 ('POST','/api/internal/submissions/{id}/reject'),('POST','/api/internal/submissions/{id}/rejudge'),
 ('PUT','/api/internal/submissions/{id}/score'),
 ('GET','/api/internal/problems/{code}/tickets'),('POST','/api/internal/problems/{code}/tickets'),
 ('GET','/api/internal/contests/{key}/tickets'),('POST','/api/internal/contests/{key}/tickets'),
 ('GET','/api/internal/tickets'),('GET','/api/internal/tickets/{id}'),('PATCH','/api/internal/tickets/{id}'),
 ('POST','/api/internal/tickets/{id}/messages'),('POST','/api/internal/tickets/{id}/claim'),
 ('POST','/api/internal/tickets/general'),('GET','/api/internal/tickets/summary')}
paths = {}
for p, item in spec['paths'].items():
    for m in ('get','post','put','patch','delete'):
        op = item.get(m)
        if op and (set(op.get('tags',[])) & KEEP_TAGS or (m.upper(), p) in EXTRA):
            paths.setdefault(p, {})[m] = op
schemas = {}
def visit(o):
    if isinstance(o, dict):
        r = o.get('$ref','')
        if r.startswith('#/components/schemas/'):
            n = r.rsplit('/',1)[1]
            if n not in schemas: schemas[n] = spec['components']['schemas'][n]; visit(schemas[n])
        for v in o.values(): visit(v)
    elif isinstance(o, list):
        for v in o: visit(v)
visit(paths)
json.dump({'openapi': {'source': 'backend-v2 <commit>'},
           'paths': dict(sorted(paths.items())),
           'components': {'schemas': dict(sorted(schemas.items()))}},
          open('references/contracts.json','w'), ensure_ascii=False, indent=1)
EOF
```

Then regenerate `references/api.md` from the new `contracts.json` (same grouping as the current file) and re-diff the behavioral claims in `permissions.md` / `workflows.md` against the changed operations.

## Drift policy

The snapshot pins two commits; production may run something else. Rules while operating:

1. A live response (schema, error code, field name) beats this snapshot — follow it and note the difference.
2. If an operation is missing or behaves differently, verify against the current backend source (controllers under `apps/api/src/modules/**`, DTOs beside them) or the site's own `openapi.json` before improvising.
3. Never probe with mutations to "test" a contract.
4. Record what differed (endpoint, expected, observed) in the final report so this skill can be updated.

## Verification status

- Verified from source at the commits above: all routes, session/capability shapes, permission catalog, access rules, field gates, quotas/rate constants, endpoint list (231 indexed), request bodies quoted in the references.
- Live-verified on `https://qhhoj.com` (2026-11-06, a staff account with organization creation rights, read-only — no mutations were performed): password login + `csrfToken`, `GET /auth/me` session shape (`isStaff`, `permissions`, `adminCapabilities`), `GET /organizations?canCreate=problem|contest` (25 orgs, `meta` pagination), `GET /problems/meta` catalog uuids, problem code → uuid resolution via `GET /problems?q=…&visibility=all` (`meta.total` 533), problem detail `allowedLanguages`, `GET /submissions`, and the 404 `not_found` error envelope. The client's offline mechanics (CSRF `csrf_failed` auto-retry, multipart `language`+`file` encoding, RFC 6238 TOTP vector) pass a local mock test.
- Not verified live: mutations (create/upload/submit/import) and Polygon flows — no test data was written to production. Treat site-specific state (settings like `problem.deleteGraceDays`, enabled contest formats, languages) as runtime data to read from the API, not from this skill.
