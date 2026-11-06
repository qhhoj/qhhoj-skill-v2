# UI routes and workflows

All UI paths below are relative to the site root (`https://qhhoj.com` by default) and were verified against the frontend router (`src/router/routes.ts`, `src/features/admin/admin-routes.ts`). Two equal ways to operate: the SPA at these routes, or the same-origin JSON API in [api.md](api.md). Use the UI to explore and verify, the API for precision; both share one session. When driving the UI, read the DOM and labels as they are — never click by coordinates or assume button names.

Admin tabs render only when the account may use them, but every rule below is enforced server-side regardless. See [permissions.md](permissions.md) for who may do what.

## Site map

| Area | Route |
| --- | --- |
| Sign in / second factor / forced password change | `/login`, `/login/2fa`, `/account/password` |
| Problems | `/problems`, problem page `/problems/{code}` (editorial is the `?tab=editorial` tab) |
| Problem admin | create `/admin/problems/new`, ZIP import `/admin/problems/import`, Polygon wizard `/admin/problems/polygon`, editor tabs `/admin/problems/{code}/general|statements|editorial|data|files|external`, deleted `/admin/problems/deleted` |
| Contests | `/contests`, contest page `/contests/{key}`, scoreboard `/contests/{key}/ranking`, submissions `/contests/{key}/submissions`, announcements `/contests/{key}/announcements`, balloons `/contests/{key}/balloons` |
| Contest admin | create `/admin/contests/new`, editor tabs `/admin/contests/{key}/general|problems|announcements|ranking|actions|participants|ghosts|data` |
| Organizations | `/organizations`, org page `/organizations/{slug}` with tabs `members`, `posts`, `submissions`, `problems`, `contests`, `quota`, `manage` |
| Submissions | `/submissions`, detail `/submissions/{id}` |
| Blog | `/blog`, compose `/blog/new`, drafts `/blog/drafts`, edit `/blog/{id}/edit` |
| Tickets | `/tickets`, new `/tickets/new`, thread `/tickets/{id}` |

`/admin/*` screens are reachable for any signed-in user with a reason to be there (staff flag, a creation capability, or an edit permission) — `isStaff` is not required; the backend still checks each object individually.

## Session bootstrap

1. Open `/login` (or reuse the browser's existing session). API equivalent: `POST /auth/login` with `{username, password}` — the answer carries the session's `csrfToken` and sets the `qhhoj_session` cookie.
2. If `twoFactorRequired` is true the session is partial (`user` is null): every page redirects to `/login/2fa`. Answer `POST /auth/2fa/totp/verify` with `{code}` (6-digit TOTP or a scratch code; the SPA strips spaces and dashes). Security keys use `POST /auth/2fa/webauthn/login/options` → browser prompt → `POST /auth/2fa/webauthn/login/verify`. Pending methods are listed in the session's `twoFactor.methods`.
3. If `passwordChangeRequired` is true every page redirects to `/account/password`; only `POST /auth/password/change` (`{currentPassword, newPassword}`) works until it is done.
4. Inspect the session with `GET /auth/me` (works during both gates). Do not treat a partial session as fully signed in, and never log credentials, cookies or CSRF tokens.

Any API answer with code `two_factor_required` or `password_change_required` means the same gates — handle the gate, never retry the mutation.

## Create a problem manually

1. **Pick the owner first.** List the organizations the account may create in: `GET /organizations?canCreate=problem` (read every page). Open `/admin/problems/new`; `?organization=<slug>` preselects that owner. If the account has no site-wide create right, the form defaults to its organization — verify the owner picker shows the intended owner before submitting.
2. Fetch the catalogs once: `GET /problems/meta` (types, groups, licenses, languages — use their ids; never invent ids). `CreateProblemDto` requires `code`, `name` (1–100), `timeLimit` (0.01–60 s), `memoryLimit` (KiB), `points` (800–3500), `typeIds` (≥ 1) and `groupId`.
3. Create: `POST /problems` (site-wide, `judge.add_problem`) or `POST /organizations/{slug}/problems` (org admin + `judge.create_organization_problem`; the server sets `organizations` and `isOrganizationPrivate` itself). Suggesters without create rights use `POST /problems/suggest`. Send only the create DTO's fields — never echo a GET response into a create body.
4. Code rules: `^[a-z0-9_]{1,32}$`, not one of the reserved codes `deleted`, `meta`, `imports`, `random`. An organization problem's code must be **strictly longer than** the org prefix — the slug's lowercase letters and digits, capped at 23 characters, followed by `_` (`thpt-a` → `thpta_`); superusers are exempt. A taken code is `code_taken`.
5. Keep the problem **private** unless publishing was asked for (`isPublic` needs `judge.change_public_visibility`). A time limit above 5 s needs `judge.high_problem_timelimit` (`time_limit_too_high`).
6. Statement (tab `/admin/problems/{code}/statements`): base statement via `PATCH /problems/{code}` (`description`, markdown ≤ 200 000 chars); translations via `PUT /problems/{code}/translations/{lang}` with `lang` = `en` or `vi`. Preview markdown with `POST /problems/render-preview`.
7. Files (tab `/admin/problems/{code}/files`): PDF statement `POST /problems/{code}/statement` (multipart `file`, PDF ≤ 5 MiB, `judge.upload_file_statement`); materials `POST .../material` (≤ 20 MiB, extension in meta's `materialExtensions`, `judge.upload_problem_material`); images for the markdown `POST /problems/uploads/image` (≤ 5 MiB JPG/PNG/GIF, SVG ≤ 512 KiB) — reference the returned `url` in the statement. An administrator who may create problems in every org of an org-private problem bypasses the statement/material permission.
8. Editorial (tab `/admin/problems/{code}/editorial`): `PUT /problems/{code}/editorial` (`content`, `isPublic`, `publishOn`, author ids). This is the official solution write-up — distinct from test data and from submissions.
9. Verify: `GET /problems/{code}` (statement, plus the `editor` block when editable), render the PDF via `GET /problems/{code}/pdf` (202 = still rendering, poll; `HEAD` never starts a render). Check language list, images and examples.

## Test data, checkers and graders

Tabs `/admin/problems/{code}/data` and `/admin/problems/{code}/files`.

1. `GET /problems/{code}/data` first. Manually managed problems answer 404 on all data routes; mirror problems use their source's data and refuse writes (403) — never flip a problem to manual or drop a mirror link on your own initiative.
2. Upload the test archive: `POST /problems/{code}/data/archive`, multipart field `file`, one `.zip` ≤ 512 MiB, fully verified server-side. It **replaces** the previous archive and counts against the org's storage and credits (`quota_exceeded`). A plain zip of tests is not a problem package — the import wizard below is for Polygon packages.
3. Upload special sources: `POST /problems/{code}/data/files/{kind}`, kind `generator` (ext `.cpp .cc .c .pas .java .py`), `customChecker` (`.cpp .pas .java`), `customGrader` (`.cpp`), `customHeader` (`.h`) — one `file` ≤ 1 MiB; wrong extension is `extension_not_allowed`, a clashing name `data_file_name_taken`. Each upload replaces the previous file of its kind; `DELETE` the same path (kind `archive` too) removes it. Archive, sources, statement, material and image uploads share a budget of **30 per hour per user**.
4. Configure cases: `PUT /problems/{code}/data` replaces the **whole** configuration — checker, grader, their args, flags, and every case (`type`: `C` case, `S` batch open, `E` batch close; `input`/`output` are file names inside the archive; `points` per case or batch). At most 300 cases (9999 with `judge.create_mass_testcases`, warn-level at 50), request body ≤ 8 MiB, all generator args combined ≤ 1 MiB. Resend the full case list every time — tests to keep must be in the body. 409 `conflict` means it changed meanwhile: reload and re-apply.
5. Validate: HTTP 200 is not success. Read `feedback` (init.yml generation error; config errors are reported here, never as HTTP errors), `sourceChecks` (checker/interactor compile status on a judge: `pending` → `ok` / `error` (see `log`) / `unavailable`), and `GET /problems/{code}/data/init` for the raw YAML (404 while none was generated). Confirm case count, file names and batch points.
6. If asked to smoke-test judging, submit an allowed solution and follow it (below). Never rejudge other people's submissions to "test".

Renaming a problem code moves the data directory first and rolls back if the save fails; caches (PDF, packages) are invalidated. Nothing to do, but don't be surprised by a transient `data_directory_taken` when the target code existed before.

## Import a Polygon package (ZIP upload)

Page `/admin/problems/import`. The zip must be a **Polygon package with `problem.xml` at its root**, ≤ 512 MiB — not an arbitrary zip of PDFs/tests. Inspect an unknown zip's listing and confirm the format before uploading.

- `POST /problems/imports`: multipart has a single field `file`; **options go in the query string** — `code` (required), `mode=create|update` (default `create`), `organization` (slug; used on create only — ignored by `update`, so never use it to move a problem), plus repeated keys (`authors`, `curators`, `typeIds`, `statementLanguages` as `<polygonLang>=en|vi|skip` pairs), `groupId`, `points`, `mainStatementLanguage`, `tutorialLanguage` and the boolean switches (`ignoreZeroPointBatches`, `ignoreZeroPointCases`, `appendMainSolution`, `importTutorial`). An empty repeated key means "not given" — on update the current values stay.
- Rights: create needs `judge.add_problem` or (with `organization`) that org's creation rights incl. the code prefix; update needs write access to the target's test data (non-mirror, non-manual). Quota: **10 imports per hour**; org credits are spent when the job queues and kept if the job fails. No Polygon-specific permission is needed for the zip route.
- The answer is **202 with a `jobId`**. Poll `GET /problems/imports/{jobId}` (never re-POST to check progress); `GET /problems/imports?mine=1` relists your jobs (kept one day). `state` is `waiting`/`active`/`delayed`/`prioritized` → `completed`/`failed`; `step` runs `queued → downloading → statements → generating → tests → done|failed` with `progress` and `queuePosition` while it runs. On completion read `result.summary` (checker mapping, clamped limits, tests/cases/batches); on failure read `errorCode`, `errorParams`, `retryable` before retrying. A timeout after submit means "find the job first", not "upload again".
- After success: `GET /problems/{code}` and `/problems/{code}/data`, review statement/translations/editorial, confirm owner org and visibility. A completed job does not replace reading `feedback`.

## Polygon linked import and sync

Page `/admin/problems/polygon` (wizard).

1. `GET /polygon/status` — whether the site's Polygon account is connected. `POST /polygon/resolve` with `{link}` (a `https://polygon.codeforces.com/p…/owner/name` URL) previews the problem, its statement languages and newest READY package. Link checks are budgeted: 20 per 10 minutes per user.
2. `POST /polygon/import` with `{link, code, mode, organization, autoSync, …zip-import options}` → 202 `jobId`, same polling as above. `autoSync=true` or `mode=update` additionally needs `judge.sync_polygon_problem`; without it send `autoSync=false`.
3. Per-problem link: `GET /problems/{code}/polygon` (link state, `runningJobId`), `PATCH` (auto-sync + import options), `DELETE` (unlink, content stays), `POST /problems/{code}/polygon/sync` (manual sync → job; body `overwriteLocalEdits` only when the user asked to discard local edits), `GET …/polygon/syncs` (history). Syncs keep code/points/classification/people and each local edit of synced settings unless overwritten; the job's `result.localEdits` lists kept vs updated.
4. Auto-sync runs every ~10 minutes as the user who enabled it and pauses while a contest using the problem is running; a later permission loss is recorded on the link, not silently skipped.

## Create and configure a contest

1. **Owner and clock first.** `GET /organizations?canCreate=contest` for orgs; open `/admin/contests/new?organization=<slug>` and verify the owner picker. Convert the user's local time to an explicit-offset timestamp and re-check what the form shows; never assume a timezone for the user.
2. Key: `^[a-z0-9_]{1,32}$`, unique, not `current` (`key_reserved`). `POST /contests` (site, `judge.add_contest`) or `POST /organizations/{slug}/contests` (org admin + `judge.create_private_contest`; the server sets `organizations=[org]` and `isOrganizationPrivate=true`, body values ignored). Required: `key`, `name` (1–100), `startTime`, `endTime` after start. Keep the contest hidden while building it.
3. Problems (tab `/admin/contests/{key}/problems`): `PATCH /contests/{key}` with the whole `problems` list — each row uses the **problem ID (uuid)** plus order, points, partial, pretest and submission-limit fields per `ContestProblemDto`; resolve codes to ids first. A problem is admittable when the editor can edit it or it is site-public; an org-private problem only when the contest is org-private, every contest org lists the problem and the editor administers all those orgs (`edit_all_contest` bypasses). Replacing the list must keep the rows to keep — scope edits re-check the kept problems.
4. General (tab `general`): format, scoring, scoreboard, registration window, dates, access codes, private list, authors/curators/testers, visibility — send only changed fields (PATCH; null is accepted only for `timeLimit`, `registrationStart/End`, `lockedAfter`, `ratingFloor`, `ratingCeiling`). Field gates: rating fields → `judge.contest_rating`; `lockedAfter` → `judge.lock_contest`; access codes → `judge.contest_access_code`; private/scope fields → `judge.create_private_contest`; making it visible → `judge.change_contest_visibility` (a private contest may be shown with `judge.create_private_contest`). Gates fire only when the value actually changes. Enum values come from the schema, not memory.
5. Announcements (tab `announcements`): `POST /contests/{key}/announcements` `{title ≤ 100, description markdown}` stores and pushes to participants (pushes limited to 20/hour per contest, resends included); `preview` first if unsure of rendering; `PATCH {id}` edits without re-pushing, `{id}/resend` re-pushes (one inbox entry per announcement), `DELETE` removes.
6. Heavy operations: read `GET /contests/{key}/actions` before/after rescore, judge-final, rate, publish-problems or replay rebuild — it reports which job is queued or running. Contest data zip and export prepare **after the contest ends** (`POST …/data`, `POST …/export` → poll state → download; once per day each).
7. Participants (tab `participants`): add/patch participations, disqualify/reinstate (send the target value — it is not a toggle), recompute; ghosts CSV import (tab `ghosts`, always `dryRun` first; download the current set as CSV to match the grammar); balloons via `/contests/{key}/balloons` (editors + balloon volunteers; a volunteer who is a contestant is refused).
8. Verify: `GET /contests/{key}` (schedule, scope, problem order/points, who can see it), scoreboard `/contests/{key}/ranking`, submissions list. Only set visibility when the request includes it and problems/data are ready; visible ≠ public while the contest is private. Never enable rating on your own initiative.

Cloning: `POST /contests/{key}/clone` (`judge.clone_contest` + edit rights; body `{key, startTime?}`, omitted start keeps the source times; the copy is hidden with you as sole author; gated fields you cannot grant are reset). Deleting a contest: `DELETE /contests/{key}?confirm=<key>` — refused for rated or live contests (`contest_not_deletable`).

## Organizations

Pages: `/organizations` (find), `/organizations/{slug}` (tabs listed in the site map).

- Read the real slug, ids, admin list and quota (`GET /organizations/{slug}`, `GET …/usage` for admins) — display names are not slugs, and the code prefix is derived from the slug, not stored.
- Create an organization only on request (`judge.add_organization`; creator is always an admin; at most 3 administered orgs per user unless `judge.spam_organization`; new orgs are unlisted until staff lists them). Membership: join open orgs (`POST …/join`; at most 3 open orgs per user), request into private ones (`POST …/requests` with `reason`, 5/hour), admins list `GET …/requests?state=P|A|R` and decide `POST …/requests/{id}/decide` with `{state: 'A'|'R'}`, kick (`POST …/kick` `{userId}`; admins cannot be kicked), leave (`POST …/leave`; the last admin is refused). These change membership — do them only when asked.
- Org problem curation: tags (`PUT …/problems/{code}/tags` with tag ids, ≤ 20 per problem; ≤ 100 tags per org), archive/unarchive (hides from the org list only — not site deletion), bulk actions (≤ 100 codes, 20/hour).
- If the requested organization is missing from `canCreate` results, open `/organizations/{slug}` to tell "does not exist" from "no rights", then report the gap. Do not silently pick another organization or the form's default.

## Submit a solution

Problem page `/problems/{code}`.

1. Languages come from the problem detail (`allowedLanguages`: `id` uuid, `key`, `fileOnly`, `fileSizeLimit` in MB). Pick an allowed, active, non-file-only language for typed source.
2. Typed: `POST /problems/{code}/submit` with `{language, source, judgeId?}` (`source` 1–65536 characters; `judgeId` is for problem editors only). File-only languages: `POST …/submit/file`, multipart with text fields `language` and optional `judgeId` plus exactly one `file` part — any order, each field at most once (repeats are `unexpected_field`); the extension must equal the language's and the size must fit `min(language.fileSizeLimit, 20 MiB)`.
3. Rate limits: 20 submissions/minute, at most 2 unfinished (`judge.spam_submission` waives); in a contest the attempt cap and `spectator_cannot_submit` apply. Don't join or leave a contest to work around an error.
4. Save the returned id and poll `GET /submissions/{id}` until a verdict (queued/judging is not accepted). Case results follow the problem's `testcaseResultVisibility`; source access is the owner's, editors', or per the problem's `submissionSourceVisibility`.

## Blog posts and tickets

- Blog: the API is **`/posts`** (`/blog` is only the UI). Start from `GET /posts/compose-options` (`canWritePersonal`, `minSolvedProblems`, orgs you may post for). `POST /posts` `{title, content, publishOn?, visible?, organization?, …}` — `organization` makes it an org post; `globalPost`/`sticky`/`summary`/`ogImage` are permission-gated; `visible:false` makes a draft. `PATCH /posts/{id}` edits; `GET /posts/drafts` lists drafts and scheduled posts. Creating and editing share 10 writes/hour. If "post" is ambiguous (blog post vs problem), ask before writing.
- Tickets: file per problem `POST /problems/{code}/tickets`, per contest `POST /contests/{key}/tickets`, general `POST /tickets/general` (5 tickets per 10 minutes); reply `POST /tickets/{id}/messages` (30 per 10 min, 500 messages per ticket); claim/release for staff and assignees. See the tickets group in [api.md](api.md).

## Destructive and bulk actions

- Problem delete: `DELETE /problems/{code}` needs `judge.delete_problem` + edit rights + body `{confirmCode}` repeating the code; restorable during the grace period (`GET /problems/deleted`, `POST …/restore`); `purge-now` is superuser-only. 10 deletes/hour. Refused while a contest uses the problem (`problem_in_contest`).
- Bulk visibility (problems/contests) and org bulk actions are rate limited and apply per-object rights — read each failed row's error code instead of re-running blindly.
- Submission overrides: rejudge/rescore/reject/lock/score-override need their `judge.*` permissions plus edit rights on the problem; score override requires a `comment` (1–500 chars). Every bulk or mass action only on explicit request; use `dryRun` where the contract offers it.
