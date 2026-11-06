# API index

Every endpoint below lives under the same origin as the site (default `https://qhhoj.com`), paths already include the `/api/internal` prefix. The table is an index only: before calling a mutation, resolve its exact request/response schema with

```bash
python3 scripts/lookup_contract.py METHOD /path      # e.g. PATCH /problems/{code}
python3 scripts/lookup_contract.py list 'contest'    # find operations by substring
```

The operation descriptions inside the snapshot embed the permission codenames, quotas, rate limits and error codes the backend enforces — read them before writing. An endpoint appearing here does not mean the current account may call it; check [permissions.md](permissions.md) first. Endpoints outside this index (system-wide admin, similarity checks, sync integrations) are out of scope: do not guess their contracts.

Groups follow the backend's own tags. `GET` list endpoints are paged with `page` (from 1) and `pageSize` unless noted.


## Authentication and session

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/internal/auth/2fa/totp/confirm` | Finish authenticator app setup |
| POST | `/api/internal/auth/2fa/totp/disable` | Turn off authenticator app sign-in |
| POST | `/api/internal/auth/2fa/totp/enroll` | Start authenticator app setup |
| GET | `/api/internal/auth/2fa/totp/scratch-codes` | Count unused scratch codes |
| POST | `/api/internal/auth/2fa/totp/scratch-codes` | Replace the scratch codes |
| POST | `/api/internal/auth/2fa/totp/verify` | Pass the second factor with a TOTP or scratch code |
| GET | `/api/internal/auth/2fa/webauthn/credentials` | List registered security keys |
| DELETE | `/api/internal/auth/2fa/webauthn/credentials/{credentialId}` | Remove a security key |
| POST | `/api/internal/auth/2fa/webauthn/login/options` | Get options to sign in with a security key |
| POST | `/api/internal/auth/2fa/webauthn/login/verify` | Pass the second factor with a security key |
| POST | `/api/internal/auth/2fa/webauthn/register/options` | Get options to register a security key |
| POST | `/api/internal/auth/2fa/webauthn/register/verify` | Register a security key |
| POST | `/api/internal/auth/activate` | Activate an account |
| POST | `/api/internal/auth/activate/resend` | Resend the activation mail |
| POST | `/api/internal/auth/impersonate/stop` | Stop impersonating |
| POST | `/api/internal/auth/impersonate/{userId}` | Impersonate a user |
| POST | `/api/internal/auth/login` | Sign in with a username and password |
| POST | `/api/internal/auth/logout` | Sign out of the current session |
| POST | `/api/internal/auth/logout-all` | Sign out of every session |
| GET | `/api/internal/auth/me` | Get the current session and user |
| POST | `/api/internal/auth/password/change` | Change the account password |
| POST | `/api/internal/auth/password/reset` | Request a password reset mail |
| POST | `/api/internal/auth/password/reset/confirm` | Set a new password from a reset link |
| POST | `/api/internal/auth/register` | Create an account |
| POST | `/api/internal/auth/social/complete` | Complete a social sign-up |
| GET | `/api/internal/auth/social/links` | List your social sign-in links |
| DELETE | `/api/internal/auth/social/links/{provider}` | Remove a social sign-in link |
| GET | `/api/internal/auth/social/providers` | List enabled social sign-in providers |
| GET | `/api/internal/auth/social/{provider}/callback` | Finish a social sign-in |
| GET | `/api/internal/auth/social/{provider}/start` | Begin a social sign-in |
| POST | `/api/internal/auth/token/regenerate` | Create a new API token |
| GET | `/api/internal/auth/username-available` | Check whether a username is free |

## Problems

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/internal/admin/licenses` | List problem licenses |
| POST | `/api/internal/admin/licenses` | Add a license |
| PATCH | `/api/internal/admin/licenses/{id}` | Update a license |
| GET | `/api/internal/admin/problem-groups` | List problem groups |
| POST | `/api/internal/admin/problem-groups` | Add a problem group |
| PATCH | `/api/internal/admin/problem-groups/{id}` | Update a problem group |
| GET | `/api/internal/admin/problem-types` | List problem types |
| POST | `/api/internal/admin/problem-types` | Add a problem type |
| PATCH | `/api/internal/admin/problem-types/{id}` | Update a problem type |
| POST | `/api/internal/organizations/{slug}/problems` | Create a problem for an organization |
| GET | `/api/internal/problems` | List problems visible to the viewer |
| POST | `/api/internal/problems` | Create a problem |
| POST | `/api/internal/problems/bulk/visibility` | Publish or unpublish problems in bulk |
| GET | `/api/internal/problems/deleted` | List deleted problems awaiting purge |
| GET | `/api/internal/problems/meta` | List the catalogs used to classify and filter problems |
| GET | `/api/internal/problems/random` | Pick a random problem code |
| POST | `/api/internal/problems/render-preview` | Render markdown to HTML for the editor preview |
| POST | `/api/internal/problems/suggest` | Suggest a problem for review |
| POST | `/api/internal/problems/uploads/image` | Upload an image for use in statements |
| DELETE | `/api/internal/problems/{code}` | Delete a problem (restorable during the grace period) |
| GET | `/api/internal/problems/{code}` | Get a problem statement and its metadata |
| PATCH | `/api/internal/problems/{code}` | Update a problem |
| POST | `/api/internal/problems/{code}/clone` | Clone a problem under a new code |
| GET | `/api/internal/problems/{code}/editorial` | Get the editorial of a problem |
| PUT | `/api/internal/problems/{code}/editorial` | Create or replace the editorial of a problem |
| DELETE | `/api/internal/problems/{code}/external-judge` | Remove a problem's external judge link |
| GET | `/api/internal/problems/{code}/external-judge` | Get a problem's external judge link |
| PUT | `/api/internal/problems/{code}/external-judge` | Set a problem's external judge link |
| POST | `/api/internal/problems/{code}/external-judge/search` | Search the external judge's problems |
| POST | `/api/internal/problems/{code}/external-judge/verify` | Verify a remote problem |
| DELETE | `/api/internal/problems/{code}/material` | Remove the downloadable material of a problem |
| POST | `/api/internal/problems/{code}/material` | Upload the downloadable material of a problem |
| GET | `/api/internal/problems/{code}/pdf` | Download the problem statement as a PDF |
| POST | `/api/internal/problems/{code}/purge-now` | Purge a deleted problem immediately |
| POST | `/api/internal/problems/{code}/restore` | Restore a deleted problem |
| DELETE | `/api/internal/problems/{code}/statement` | Remove the PDF statement of a problem |
| POST | `/api/internal/problems/{code}/statement` | Upload the PDF statement of a problem |
| PUT | `/api/internal/problems/{code}/translations/{lang}` | Create or replace a statement translation |

## Problem test data and packages

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/internal/problems/{code}/data` | Get the test data configuration of a problem |
| PUT | `/api/internal/problems/{code}/data` | Replace the test data configuration of a problem |
| POST | `/api/internal/problems/{code}/data/archive` | Upload the test data archive of a problem |
| DELETE | `/api/internal/problems/{code}/data/files/{kind}` | Remove an uploaded data file |
| POST | `/api/internal/problems/{code}/data/files/{kind}` | Upload a generator, checker, grader or header file |
| GET | `/api/internal/problems/{code}/data/files/{name}` | Download an uploaded test data file |
| GET | `/api/internal/problems/{code}/data/init` | Get the generated init.yml of a problem |
| GET | `/api/internal/problems/{code}/package` | Download the package of a problem |
| POST | `/api/internal/problems/{code}/package` | Request a downloadable package of a problem |

## Problem imports (Polygon ZIP)

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/internal/problems/imports` | List my Polygon imports and syncs |
| POST | `/api/internal/problems/imports` | Import a Polygon package as a new or existing problem |
| GET | `/api/internal/problems/imports/{jobId}` | Get the state of a Polygon import job |

## Polygon

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/internal/polygon/import` | Import a Polygon problem and link it |
| POST | `/api/internal/polygon/resolve` | Check a Polygon problem link and preview the problem |
| GET | `/api/internal/polygon/status` | Get whether the Polygon account is connected |
| GET | `/api/internal/polygon/syncs` | List the Polygon sync history of every problem |
| DELETE | `/api/internal/problems/{code}/polygon` | Unlink a problem from Polygon |
| GET | `/api/internal/problems/{code}/polygon` | Get a problem's Polygon link |
| PATCH | `/api/internal/problems/{code}/polygon` | Change a problem's Polygon auto-sync and import options |
| POST | `/api/internal/problems/{code}/polygon/sync` | Sync a linked problem from Polygon |
| GET | `/api/internal/problems/{code}/polygon/syncs` | List a problem's Polygon sync history |

## Contests: viewing and taking part

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/internal/contest-tags` | List contest tags |
| POST | `/api/internal/contest-tags` | Create a contest tag |
| DELETE | `/api/internal/contest-tags/{slug}` | Delete a contest tag |
| PATCH | `/api/internal/contest-tags/{slug}` | Update a contest tag |
| GET | `/api/internal/contests` | List the contests visible to the viewer |
| GET | `/api/internal/contests/current` | Get the contest the viewer is currently in |
| GET | `/api/internal/contests/{key}` | Get a contest by key |
| GET | `/api/internal/contests/{key}/announcements` | List the announcements of a contest |
| POST | `/api/internal/contests/{key}/announcements` | Post a contest announcement |
| POST | `/api/internal/contests/{key}/announcements/preview` | Preview an announcement |
| DELETE | `/api/internal/contests/{key}/announcements/{id}` | Delete a contest announcement |
| PATCH | `/api/internal/contests/{key}/announcements/{id}` | Edit a contest announcement |
| POST | `/api/internal/contests/{key}/announcements/{id}/resend` | Resend a contest announcement |
| POST | `/api/internal/contests/{key}/join` | Join a contest |
| POST | `/api/internal/contests/{key}/leave` | Leave the current contest |
| GET | `/api/internal/contests/{key}/participations` | List participations in a contest |
| POST | `/api/internal/contests/{key}/participations/disqualify` | Disqualify or reinstate many participants |
| POST | `/api/internal/contests/{key}/participations/{id}/disqualify` | Disqualify or reinstate a participant |
| GET | `/api/internal/contests/{key}/problems/{code}/best-submissions` | List the best submission of each user on a contest problem |
| GET | `/api/internal/contests/{key}/ranking` | Get the ranking of a contest |
| POST | `/api/internal/contests/{key}/register` | Register for a contest |
| GET | `/api/internal/contests/{key}/replay` | Get the replay of a contest |
| POST | `/api/internal/contests/{key}/replay/rebuild` | Rebuild the replay of a contest |
| GET | `/api/internal/contests/{key}/stats` | Get the statistics of a contest |
| GET | `/api/internal/contests/{key}/submissions` | List the submissions of a contest |

## Contests: editing and operations

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/internal/contests` | Create a contest |
| POST | `/api/internal/contests/bulk/tag` | Add or remove a tag on contests in bulk |
| POST | `/api/internal/contests/bulk/visibility` | Show or hide contests in bulk |
| DELETE | `/api/internal/contests/{key}` | Delete a contest |
| PATCH | `/api/internal/contests/{key}` | Update a contest |
| GET | `/api/internal/contests/{key}/actions` | Get the available editor actions of a contest |
| GET | `/api/internal/contests/{key}/balloons` | List the balloon queue of a contest |
| POST | `/api/internal/contests/{key}/balloons/{participation}/{problem}/deliver` | Mark a balloon as delivered |
| POST | `/api/internal/contests/{key}/balloons/{participation}/{problem}/undeliver` | Mark a balloon as not delivered |
| POST | `/api/internal/contests/{key}/clone` | Clone a contest |
| GET | `/api/internal/contests/{key}/data` | Get the state of the contest data download |
| POST | `/api/internal/contests/{key}/data` | Prepare the contest data download |
| GET | `/api/internal/contests/{key}/data/download` | Download the contest data |
| GET | `/api/internal/contests/{key}/export` | Get the state of the contest export |
| POST | `/api/internal/contests/{key}/export` | Request a contest export |
| GET | `/api/internal/contests/{key}/export/download` | Download the contest export |
| GET | `/api/internal/contests/{key}/feed` | Get the event feed of a contest |
| DELETE | `/api/internal/contests/{key}/feed-key` | Revoke the feed keys of a contest |
| GET | `/api/internal/contests/{key}/feed-key` | Get the feed key status of a contest |
| POST | `/api/internal/contests/{key}/feed-key` | Create a feed key for a contest |
| POST | `/api/internal/contests/{key}/feed-key/release` | Release the feed to the resolver |
| DELETE | `/api/internal/contests/{key}/ghosts` | Delete all ghosts of a contest |
| GET | `/api/internal/contests/{key}/ghosts` | List the ghosts of a contest |
| PUT | `/api/internal/contests/{key}/ghosts` | Import ghost participants from CSV |
| GET | `/api/internal/contests/{key}/ghosts/csv` | Download the ghosts as CSV |
| POST | `/api/internal/contests/{key}/judge-final` | Judge the final submissions of a contest |
| DELETE | `/api/internal/contests/{key}/official-ranking` | Delete the official ranking |
| GET | `/api/internal/contests/{key}/official-ranking` | Get the official ranking of a contest |
| PUT | `/api/internal/contests/{key}/official-ranking` | Upload the official ranking |
| POST | `/api/internal/contests/{key}/participations` | Add a participation |
| DELETE | `/api/internal/contests/{key}/participations/{id}` | Delete a participation |
| PATCH | `/api/internal/contests/{key}/participations/{id}` | Change a participation's start |
| POST | `/api/internal/contests/{key}/participations/{id}/recompute` | Recompute a participation |
| POST | `/api/internal/contests/{key}/problems/{code}/rejudge` | Rejudge a contest problem's submissions |
| POST | `/api/internal/contests/{key}/problems/{code}/rescore` | Rescore a contest problem |
| POST | `/api/internal/contests/{key}/publish-problems` | Publish the problems of an ended contest |
| GET | `/api/internal/contests/{key}/ranking-link` | Get the public ranking link settings |
| PATCH | `/api/internal/contests/{key}/ranking-link` | Update the public ranking link settings |
| POST | `/api/internal/contests/{key}/ranking-link` | Create the public ranking link |
| POST | `/api/internal/contests/{key}/ranking-link/regenerate` | Regenerate the public ranking link token |
| POST | `/api/internal/contests/{key}/rate` | Rate a contest |
| POST | `/api/internal/contests/{key}/rescore` | Rescore a contest |
| POST | `/api/internal/organizations/{slug}/contests` | Create a contest for an organization |
| GET | `/api/internal/public-rankings/{token}` | Get a ranking through its public link |

## Organizations

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/internal/admin/organization-requests` | List join requests across organizations |
| GET | `/api/internal/organizations` | List organizations |
| POST | `/api/internal/organizations` | Create an organization |
| POST | `/api/internal/organizations/render-preview` | Preview an organization's about text |
| GET | `/api/internal/organizations/usage` | List quota usage of all organizations |
| DELETE | `/api/internal/organizations/{slug}` | Delete an organization |
| GET | `/api/internal/organizations/{slug}` | Get an organization by slug |
| PATCH | `/api/internal/organizations/{slug}` | Edit an organization |
| POST | `/api/internal/organizations/{slug}/join` | Join an open organization |
| POST | `/api/internal/organizations/{slug}/kick` | Remove a member from an organization |
| POST | `/api/internal/organizations/{slug}/leave` | Leave an organization |
| GET | `/api/internal/organizations/{slug}/members` | List the members of an organization |
| GET | `/api/internal/organizations/{slug}/problem-tags` | List the problem tags of an organization |
| POST | `/api/internal/organizations/{slug}/problem-tags` | Create a problem tag |
| DELETE | `/api/internal/organizations/{slug}/problem-tags/{tagSlug}` | Delete a problem tag |
| PATCH | `/api/internal/organizations/{slug}/problem-tags/{tagSlug}` | Update a problem tag |
| GET | `/api/internal/organizations/{slug}/problems` | List the problems of an organization |
| POST | `/api/internal/organizations/{slug}/problems/bulk` | Apply a bulk action to organization problems |
| DELETE | `/api/internal/organizations/{slug}/problems/{code}/archive` | Unarchive a problem in an organization |
| POST | `/api/internal/organizations/{slug}/problems/{code}/archive` | Archive a problem in an organization |
| PUT | `/api/internal/organizations/{slug}/problems/{code}/tags` | Set the tags of an organization problem |
| PATCH | `/api/internal/organizations/{slug}/quota` | Change the quota of an organization |
| POST | `/api/internal/organizations/{slug}/recalculate` | Recalculate an organization's points and member count |
| GET | `/api/internal/organizations/{slug}/requests` | List the join requests of an organization |
| POST | `/api/internal/organizations/{slug}/requests` | Request to join a private organization |
| GET | `/api/internal/organizations/{slug}/requests/{id}` | Get a join request |
| POST | `/api/internal/organizations/{slug}/requests/{id}/decide` | Approve or reject a join request |
| GET | `/api/internal/organizations/{slug}/revisions` | List an organization's change history |
| GET | `/api/internal/organizations/{slug}/submissions` | List the submissions of an organization's members |
| GET | `/api/internal/organizations/{slug}/usage` | Get the quota usage of an organization |
| GET | `/api/internal/problems/{code}/archived-in` | List the viewer's organizations that archived a problem |

## Submissions and judging

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/internal/problems/{code}/best-submissions` | List the best submission of each user on a problem |
| POST | `/api/internal/problems/{code}/submit` | Submit a solution as typed source code |
| POST | `/api/internal/problems/{code}/submit/file` | Submit a solution as an uploaded file |
| GET | `/api/internal/runtimes` | Get the judges and the languages they run |
| GET | `/api/internal/submissions` | List submissions visible to the viewer |
| GET | `/api/internal/submissions/batches/recent` | List recent bulk rejudges and rescores |
| POST | `/api/internal/submissions/rejudge` | Rejudge many submissions |
| POST | `/api/internal/submissions/rescore` | Recalculate the points of many submissions |
| GET | `/api/internal/submissions/stats` | Get the judging figures shown above the submission list |
| GET | `/api/internal/submissions/{id}` | Get a submission with its judging details |
| POST | `/api/internal/submissions/{id}/abort` | Abort a submission that is waiting or being judged |
| DELETE | `/api/internal/submissions/{id}/lock` | Unlock a submission |
| POST | `/api/internal/submissions/{id}/lock` | Lock a submission |
| POST | `/api/internal/submissions/{id}/reject` | Reject a submission |
| POST | `/api/internal/submissions/{id}/rejudge` | Rejudge one submission |
| PUT | `/api/internal/submissions/{id}/score` | Override a submission's verdict and score |
| GET | `/api/internal/submissions/{id}/source` | Get the source code of a submission |
| GET | `/api/internal/submissions/{id}/source/download` | Download the source code as a file |
| GET | `/api/internal/submissions/{id}/source/raw` | Show the source code as plain text |

## Tickets

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/internal/contests/{key}/tickets` | List the tickets filed from a contest |
| POST | `/api/internal/contests/{key}/tickets` | Ask a contest's organisers |
| GET | `/api/internal/problems/{code}/tickets` | List the tickets of a problem |
| POST | `/api/internal/problems/{code}/tickets` | File a ticket about a problem |
| GET | `/api/internal/tickets` | List tickets |
| POST | `/api/internal/tickets/general` | File a general ticket |
| GET | `/api/internal/tickets/summary` | Get the ticket badge counts |
| GET | `/api/internal/tickets/{id}` | Get a ticket |
| PATCH | `/api/internal/tickets/{id}` | Update a ticket |
| POST | `/api/internal/tickets/{id}/claim` | Take a ticket |
| POST | `/api/internal/tickets/{id}/messages` | Reply to a ticket |

## Blog posts

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/internal/admin/posts` | List posts awaiting moderation |
| GET | `/api/internal/organizations/{slug}/posts` | List the posts of an organization |
| GET | `/api/internal/posts` | List blog posts |
| POST | `/api/internal/posts` | Create a blog post |
| GET | `/api/internal/posts/compose-options` | Get where I may post |
| GET | `/api/internal/posts/drafts` | List my drafts |
| DELETE | `/api/internal/posts/{id}` | Delete a blog post |
| GET | `/api/internal/posts/{id}` | Get a blog post |
| PATCH | `/api/internal/posts/{id}` | Edit a blog post |
| PUT | `/api/internal/posts/{id}/vote` | Vote on a blog post |
