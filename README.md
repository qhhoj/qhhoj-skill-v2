# qhhoj-skill-v2

An [Agent Skills](https://agentskills.io/specification)-format skill that lets an agent operate the QHHOJ v2 online-judge site (`https://qhhoj.com`, source: [qhhoj/frontend-v2](https://github.com/qhhoj/frontend-v2) + [qhhoj/backend-v2](https://github.com/qhhoj/backend-v2)) with a user's account: sign in (2FA/password gates), create and edit problems, upload test archives/checkers/statements/materials, import Polygon packages, create contests site-wide or inside organizations, manage organizations, submit solutions, rejudge/rescore, write blog posts, file tickets — each only as far as the account's permissions, field gates and quotas allow.

Not the legacy stack: for the old Django/DMOJ site (`qhhoj/online-judge`, `/api/v2`) use [qhhoj/qhhoj-skill](https://github.com/qhhoj/qhhoj-skill) instead.

## Layout

```
SKILL.md                     # start here: quick start, operating loop, core mechanics, doc map
references/permissions.md    # session shape, permission catalog, field gates, quotas, error playbook
references/workflows.md      # verified UI routes + step-by-step recipes
references/api.md            # index of 231 /api/internal operations
references/contracts.json    # scoped OpenAPI snapshot (the machine truth)
references/sources.md        # provenance (commits), live-verification log, refresh & drift policy
scripts/qhhoj_client.py      # ready HTTP client: login/2FA, creates, uploads, submits, job polling
scripts/lookup_contract.py   # exact schemas for one operation: `list <word>` / `METHOD /path`
```

## Using it

Install as a skill (directory name = skill name) or read `SKILL.md` directly. The client needs Python 3 + `requests`; the lookup script is stdlib-only:

```bash
python3 scripts/qhhoj_client.py https://qhhoj.com user pass [--totp SECRET]   # read-only probe
python3 scripts/qhhoj_client.py https://qhhoj.com --token API_TOKEN
python3 scripts/lookup_contract.py POST /organizations/{slug}/contests
python3 scripts/lookup_contract.py list polygon
```

The snapshot was generated from `backend-v2/openapi.json` at commit `867fd75` and the flows were live-checked against `qhhoj.com` (see `references/sources.md` for the log, the regeneration script and the drift policy).
