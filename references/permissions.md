# Session, permissions and refusals

## Reading the session

`GET /api/internal/auth/me` (works while a second factor or password change is pending) returns `data`:

- `user` — **null while 2FA is pending**; otherwise: `id, username, rating, email, isStaff, isSuperuser, permissions` (sorted codenames, direct + through groups), `adminCapabilities, isTotpEnabled, isWebauthnEnabled, …`.
- `csrfToken` — send as `X-CSRF-Token` on every non-GET request from this cookie session (null for API-token sessions, which skip CSRF).
- `twoFactorRequired`, `twoFactor: {username, methods: ['totp'|'webauthn']}`, `passwordChangeRequired`, `impersonatorId`.

`adminCapabilities` (`session-responses.service.ts`): `organizations: boolean` (administers ≥ 1 org or holds `judge.edit_all_organization`); `problemCreation: {site, organizations}` — `site` = `judge.add_problem`, `organizations` = administers an org **and** holds `judge.create_organization_problem`; `contestCreation` likewise with `judge.add_contest` / `judge.create_private_contest`. These capabilities open the admin screens; they are not per-object rights, and while 2FA is pending they read as false. Do not infer permissions from group names, staff badges or visible buttons — read `permissions` and test per-object access with GETs.

`isSuperuser` satisfies every permission codename, and exempts from the org code prefix; business rules (quotas, contest membership, in-flight jobs) still apply. Organization membership is not part of the session response — read it from the organization endpoints.

## Permission layers

1. **System permission codenames** (from `libs/auth/src/principal/permissions.ts`) — the operator-relevant ones:

   | Area | Codenames |
   | --- | --- |
   | Problems | `judge.add_problem`, `judge.suggest_new_problem`, `judge.edit_own_problem`, `judge.edit_all_problem`, `judge.edit_public_problem`, `judge.create_organization_problem`, `judge.clone_problem`, `judge.delete_problem`, `judge.change_public_visibility`, `judge.change_manually_managed`, `judge.problem_full_markup`, `judge.high_problem_timelimit`, `judge.create_mass_testcases`, `judge.upload_file_statement`, `judge.upload_problem_material`, `judge.sync_polygon_problem`, `judge.see_private_problem`, `judge.see_organization_problem`, `judge.see_private_solution`, `judge.add_tagproblem` |
   | Contests | `judge.add_contest`, `judge.create_private_contest`, `judge.edit_own_contest`, `judge.edit_all_contest`, `judge.clone_contest`, `judge.change_contest_visibility`, `judge.contest_rating`, `judge.contest_access_code`, `judge.lock_contest`, `judge.change_contest_tag`, `judge.contest_problem_label`, `judge.long_contest_duration`, `judge.see_private_contest`, `judge.moss_contest` |
   | Organizations | `judge.add_organization`, `judge.edit_all_organization`, `judge.organization_admin`, `judge.change_open_organization`, `judge.spam_organization` |
   | Judging | `judge.rejudge_submission`, `judge.rejudge_submission_lot`, `judge.reject_submission`, `judge.lock_submission`, `judge.change_submission`, `judge.abort_any_submission`, `judge.spam_submission`, `judge.view_all_submission`, `judge.resubmit_other`, `judge.change_judge` (rescore endpoints need only edit rights on the scope) |
   | Community | `judge.edit_organization_post`, `judge.edit_all_post`, `judge.mark_global_post`, `judge.pin_post`, `judge.delete_blogpost`, `judge.change_ticket`, `judge.can_upload_image` |

2. **Per-object relations** — author ∪ curator (problems, contests), suggester (problems), tester (contests: preview only), organization `adminIds`. Org administration = `adminIds` contains you or `judge.edit_all_organization`.
3. **Per-field gates** — a write may be allowed but a specific field locked (tables below). Gates fire only when the value actually changes.

## Action requirements
| Action | Requirements beyond being signed in |
| --- | --- |
| Create problem, site-wide | `judge.add_problem` (`POST /problems`) |
| Suggest a problem | `judge.suggest_new_problem` (`POST /problems/suggest`; stored private, you are the suggester) |
| Create problem in an org | Administer the org **and** `judge.create_organization_problem`; code must extend the org prefix; org quota is charged |
| Edit a problem | `judge.edit_own_problem` **and** (author ∪ curator ∪ suggester, or `judge.edit_all_problem`, or `judge.edit_public_problem` with `isPublic=true`) |
| View test data / data routes | Problem edit rights (seeing the statement is not enough); manual problems 404, mirrors read-only |
| Clone problem / contest | `judge.clone_problem` / `judge.clone_contest` + edit rights on the source |
| Delete problem | `judge.delete_problem` + edit rights + `confirmCode`; restore same rights |
| Create contest, site-wide | `judge.add_contest` |
| Create contest in an org | Administer the org **and** `judge.create_private_contest` (no `judge.add_contest` needed); scope set server-side |
| Edit a contest | `judge.edit_all_contest`, or `judge.edit_own_contest` **and** author ∪ curator. Testers never edit |
| Org administration | In `adminIds` or `judge.edit_all_organization`; ordinary members have none |
| Rejudge / rescore | `judge.rejudge_submission` (+ `judge.rejudge_submission_lot` beyond 10 matches) + edit rights on the problem/contest scope; site-wide batch needs `judge.edit_all_problem` |
| Score override / reject / lock | `judge.change_submission` / `judge.reject_submission` / `judge.lock_submission` + problem edit rights |
| Blog post | Personal: solved-problem minimum + unmuted. Org: unmuted org admin + `judge.edit_organization_post` (`GET /posts/compose-options` is authoritative) |
| Org join/request | Any signed-in user; open join capped at 3 open orgs; requests 5/hour |

## Field-level gates

Problem (`PATCH /problems/{code}` and create):

| Field(s) | Extra permission |
| --- | --- |
| `isPublic` | `judge.change_public_visibility` |
| `isManuallyManaged` | `judge.change_manually_managed` |
| `isFullMarkup` | `judge.problem_full_markup` |
| `timeLimit` > 5 s | `judge.high_problem_timelimit` |
| `authors, curators, bannedUsers, licenseId, summary, ogImage, allowedLanguages, organizations, isOrganizationPrivate, testcaseResultVisibility, allowViewFeedback, date` | `judge.edit_all_problem` (org-problem create lets org admins name org admins without it) |
| Leaving org privacy so the problem becomes visible to everyone | `judge.change_public_visibility` even with `judge.edit_all_problem` (`site_publish_rights`) |
| Moving org ↔ org / org ↔ site | Creation rights in every org added/removed; leaving all orgs needs `judge.add_problem` (`site_problem_rights`) |
| > 300 test cases | `judge.create_mass_testcases` |

Contest (`PATCH /contests/{key}`): rating fields (`isRated, rateAll, rateExclude, ratingFloor, ratingCeiling`) → `judge.contest_rating`; `lockedAfter` → `judge.lock_contest`; `accessCode`/`rankingAccessCode` → `judge.contest_access_code`; `isPrivate, privateContestants, isOrganizationPrivate, organizations` → `judge.create_private_contest`; `isVisible` → `judge.change_contest_visibility` (a private contest may be shown with `judge.create_private_contest`).

Blog post: `globalPost` → `judge.mark_global_post`; `sticky` → `judge.pin_post`; `summary`/`ogImage` → `judge.edit_all_post`.

## Visibility scoping

- **Problem**: site-public = `isPublic && !isOrganizationPrivate`. An org-private problem (`isPublic=true, isOrganizationPrivate=true`) is visible to its orgs' members (+ `judge.see_organization_problem`, editors, testers, contest scope). 404 hides existence; 403 means "visible but not allowed".
- **Contest**: `isVisible` (listed at all), `isPrivate` (+ invited `privateContestants`), `isOrganizationPrivate` (+ `organizations`). Both private flags ⇒ a normal participant must pass both. Authors/curators/testers and editors see through; frozen scoreboards limit non-editors.
- **Organization**: `isUnlisted` orgs are missing from the public list but reachable by slug; not the same as private.
- Never widen scope to work around a 403/404, and don't read hidden scoreboards or others' sources by URL-crafting.

## Organization prefix and quota

- Org problem codes: prefix = the slug's `[a-z0-9]` characters (first 23) + `_`; the code must be strictly longer; superusers exempt. Org slug pattern `^[A-Za-z][-A-Za-z0-9_]*$`, unique case-insensitively.
- Quotas per org per month: credits (10 MiB of stored data = 1 credit), judging milliseconds, storage bytes; enforced on create/upload/import/move (`quota_exceeded`). Read `GET /organizations/{slug}/usage` before heavy operations; quota can block an action the permission table allows. Never switch orgs to dodge a quota.

## Rate limits and budgets (per user unless noted)

| Budget | Limit |
| --- | --- |
| Login failures | 10/15 min per account+network, 300/15 min per IP; successful logins 20/15 min per account |
| 2FA attempts | 10/15 min and 50/day |
| Data/statement/material/image uploads | 30/hour, shared |
| Polygon package imports + syncs | 10/hour; link checks 20/10 min |
| Problem deletes | 10/hour |
| Submissions | 20/min; 2 unfinished concurrently |
| Blog writes (create+edit) | 10/hour |
| Organization join requests | 5/hour; about-preview 60/min |
| Contest announcement pushes (per contest) | 20/hour incl. resends |
| Tickets / ticket messages | 5 per 10 min / 30 per 10 min |
| Markdown render previews | 60/min |
| Bulk runs (visibility, tag, disqualify, org bulk) | 20/hour |
| Contest data/export builds | 1/day each, after the contest ends |
| JSON bodies | 1 MiB default, 8 MiB for `PUT /problems/{code}/data`; any multipart ≤ 20 MiB except archives/packages (512 MiB) |

On 429 read `Retry-After` and wait; never spawn parallel jobs to poll faster.

## Error handling

Envelope: `{error: {code, message, fields?, issues?, …extra}}`; `issues[]` carries machine codes per field or one request-level code. `Retry-After` header accompanies 429/503.

| Situation | Response |
| --- | --- |
| 401 `unauthorized` | Session gone — sign in again; do not repeat the mutation blindly |
| `two_factor_required` / `password_change_required` | Complete the gate via its flow; a partial session is not signed in |
| 403 `csrf_failed` | Reload `GET /auth/me` for a fresh token and resend **once** (the SPA retries exactly once) |
| 403 `forbidden` / quota codes | Right or quota missing — report which field/action is blocked; never bypass, impersonate or self-escalate |
| 404 | Unknown, invisible, manual-managed data, or not-yet-generated resource — check context before concluding "deleted" |
| 400 `validation_failed` | Fix the exact `fields`/`issues`; keep unrelated fields unchanged |
| 409 `conflict` | Someone changed the object — re-GET, reconcile, retry; never blind-overwrite |
| 429 / 503 with `Retry-After` | Wait; polling is free, re-submitting is not |
| Timeout after a mutation | GET the object/job by id and check whether it was written **before** retrying (avoid duplicates) |

## Safety rules

- Operate only the account and site you were given; stay inside the user's request — technical ability (a permission you hold) is not authorization to publish, notify, rejudge, delete or change rights.
- Never start impersonation, change security settings, or log out other sessions when the task is content work. If `impersonatorId` is set in the session, mention it in your report.
- Keep credentials, cookies, CSRF tokens, unreleased statements/tests and ranking/feed keys out of logs and reports.
- Report each result with the object URL, the owning organization, visibility state, job ids and anything blocked with the backend's own error code.
