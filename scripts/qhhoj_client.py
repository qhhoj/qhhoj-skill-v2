#!/usr/bin/env python3
"""QHHOJ v2 site client — same-origin JSON API automation (browser-free).

Self-contained: stdlib + `requests` (no pyotp; TOTP is implemented inline).
Field names and flows verified against the source of
https://github.com/qhhoj/backend-v2 @ 867fd75 (contract: openapi.json).

Two auth modes:
  - session (default): POST /api/internal/auth/login (+ TOTP second factor),
    cookie qhhoj_session + X-CSRF-Token on every non-GET — like the SPA;
  - API token: QhhojClient(url, api_token='…') sends Authorization: Bearer;
    no CSRF needed, but @SessionOnly() endpoints (e.g. feed keys) refuse it.

Usage:
    from qhhoj_client import QhhojClient
    c = QhhojClient('https://qhhoj.com', 'user', 'pass')   # totp_secret='JBSW…' if 2FA
    c.login()
    orgs = c.creation_organizations('problem')
    c.create_problem(code='demo_aplusb', name='A + B', time_limit=2,
                     memory_limit=262144, points=1000,
                     type_ids=[type_id], group_id=group_id,
                     description='Compute $A+B$.')
    c.upload_archive('demo_aplusb', 'tests.zip')
    c.put_data('demo_aplusb', cases=[case('C', '1.in', '1.ans', 100)])
    pid = c.problem_id('demo_aplusb')
    c.create_contest(key='demo', name='Demo Contest',
                     start='2026-11-07T09:00:00+07:00',
                     end='2026-11-07T12:00:00+07:00')
    c.set_contest_problems('demo', [(pid, 100)])
    c.announce('demo', 'Round started', 'Good luck!')
    sid = c.submit('demo_aplusb', 'print(int(input()) + int(input()))')
    print(c.wait_for_verdict(sid))

CLI probe (read-only after login):
    python3 qhhoj_client.py https://qhhoj.com user pass [--totp SECRET]
    python3 qhhoj_client.py https://qhhoj.com --token '…'
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import struct
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.parse import quote

import requests

API = '/api/internal'
TERMINAL_STATES = ('completed', 'failed')


class QhhojError(Exception):
    """Backend refusal or client-side precondition failure.

    Carries .code (snake_case machine code), .status (HTTP), .fields,
    .issues and .retry_after when the backend sent them.
    """

    def __init__(self, message: str, *, code: str = 'client_error',
                 status: int = 0, fields: dict | None = None,
                 issues: list | None = None, retry_after: int | None = None):
        super().__init__(message)
        self.code, self.status = code, status
        self.fields, self.issues, self.retry_after = fields, issues, retry_after


def totp(secret: str, step: int = 30, digits: int = 6, t: int | None = None) -> str:
    """RFC 6238 SHA-1 TOTP from a base32 secret (pyotp-free)."""
    key = base64.b32decode(secret.upper() + '=' * (-len(secret) % 8), casefold=True)
    counter = struct.pack('>Q', int((time.time() if t is None else t) // step))
    digest = hmac.new(key, counter, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (struct.unpack('>I', digest[offset:offset + 4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(code).zfill(digits)


def case(type_: str, input_: str = '', output: str = '',
         points: float | None = None, is_pretest: bool = False,
         generator_args: str = '', checker: str = '', checker_args: dict | None = None,
         output_prefix: int | None = None, output_limit: int | None = None) -> dict:
    """Build one TestCaseDto: type 'C' case, 'S' batch open, 'E' batch close."""
    row = {'type': type_}
    for key, value in (('input', input_), ('output', output), ('points', points),
                       ('isPretest', is_pretest), ('generatorArgs', generator_args),
                       ('checker', checker), ('checkerArgs', checker_args),
                       ('outputPrefix', output_prefix), ('outputLimit', output_limit)):
        if value not in (None, ''):
            row[key] = value
    return row


class QhhojClient:
    def __init__(self, base_url: str, username: str | None = None,
                 password: str | None = None, *, totp_secret: str | None = None,
                 api_token: str | None = None, timeout: int = 30):
        self.base = base_url.rstrip('/')
        self.username, self.password, self.totp_secret = username, password, totp_secret
        self.api_token = api_token
        self.timeout = timeout
        self.s = requests.Session()
        self.csrf: Optional[str] = None
        self.user: Optional[dict] = None

    # ---------------- low level ----------------

    def url(self, path: str) -> str:
        return self.base + (path if path.startswith(API) else API + '/' + path.lstrip('/'))

    def _headers(self, method: str) -> dict:
        headers = {'Accept': 'application/json'}
        if self.api_token:
            headers['Authorization'] = 'Bearer ' + self.api_token
        elif method != 'GET':
            if self.csrf:
                headers['X-CSRF-Token'] = self.csrf
            headers['Origin'] = self.base  # a wrong Origin is rejected outright
        return headers

    def request(self, method: str, path: str, *, params: dict | None = None,
                body: Any = None, form: dict | None = None, file: tuple | None = None,
                _retry: bool = True) -> Any:
        """Send one request; unwrap the {data, meta} envelope; raise QhhojError
        on {error: …} answers. Multipart: `form` fields + exactly one `file`."""
        method = method.upper()
        kwargs: dict = {'params': params, 'headers': self._headers(method),
                        'timeout': self.timeout}
        if file is not None or form is not None:
            if file is not None:
                kwargs['files'] = {'file': file}
            if form is not None:
                kwargs['data'] = form  # multipart text fields
        elif body is not None:
            kwargs['json'] = body
        r = self.s.request(method, self.url(path), **kwargs)
        if (r.status_code == 403 and _retry and not self.api_token
                and self._error_code(r) == 'csrf_failed'):  # SPA behaviour: refresh once
            self.fetch_session()
            return self.request(method, path, params=params, body=body,
                                form=form, file=file, _retry=False)
        if r.status_code == 204 or not r.content:
            return None
        try:
            payload = r.json()
        except ValueError:
            raise QhhojError(f'{method} {path}: non-JSON answer ({r.status_code})',
                             code='invalid_response', status=r.status_code) from None
        if isinstance(payload, dict) and 'error' in payload:
            e = payload['error']
            raise QhhojError(e.get('message') or e.get('code') or 'request failed',
                             code=e.get('code', 'http_error'), status=r.status_code,
                             fields=e.get('fields'), issues=e.get('issues'),
                             retry_after=int(r.headers.get('Retry-After', 0) or 0) or None)
        if not (200 <= r.status_code < 300):
            raise QhhojError(f'{method} {path}: HTTP {r.status_code}',
                             code='http_error', status=r.status_code)
        return payload.get('data', payload) if isinstance(payload, dict) else payload

    def get(self, path: str, **kw) -> Any:
        return self.request('GET', path, **kw)

    def post(self, path: str, body: Any = None, **kw) -> Any:
        return self.request('POST', path, body=body, **kw)

    def patch(self, path: str, body: Any = None, **kw) -> Any:
        return self.request('PATCH', path, body=body, **kw)

    def put(self, path: str, body: Any = None, **kw) -> Any:
        return self.request('PUT', path, body=body, **kw)

    def delete(self, path: str, body: Any = None, **kw) -> Any:
        return self.request('DELETE', path, body=body, **kw)

    @staticmethod
    def _error_code(r: requests.Response) -> str | None:
        try:
            return r.json().get('error', {}).get('code')
        except ValueError:
            return None

    def get_page(self, path: str, params: dict | None = None,
                 page: int = 1, page_size: int = 100) -> tuple[list, dict]:
        """One page of a paged list endpoint; returns (rows, meta).
        Reads the raw envelope so `meta` survives the default unwrapping."""
        params = dict(params or {})
        params.update({'page': page, 'pageSize': page_size})
        r = self.s.get(self.url(path), params=params,
                       headers=self._headers('GET'), timeout=self.timeout)
        try:
            payload = r.json()
        except ValueError:
            raise QhhojError(f'GET {path}: non-JSON answer ({r.status_code})',
                             code='invalid_response', status=r.status_code) from None
        if isinstance(payload, dict) and 'error' in payload:
            e = payload['error']
            raise QhhojError(e.get('message') or e.get('code') or 'request failed',
                             code=e.get('code', 'http_error'), status=r.status_code,
                             fields=e.get('fields'), issues=e.get('issues'))
        if isinstance(payload, list):
            return payload, {}
        payload = payload or {}
        return payload.get('data') or [], payload.get('meta') or {}

    def paged(self, path: str, params: dict | None = None,
              page_size: int = 100) -> Iterable[dict]:
        """Yield every row of a paged list endpoint, following meta.total."""
        page = 1
        while True:
            rows, meta = self.get_page(path, params, page=page, page_size=page_size)
            yield from rows
            total = meta.get('total')
            if len(rows) < page_size or (total is not None and page * page_size >= total):
                return
            page += 1

    # ---------------- auth ----------------

    def fetch_session(self) -> dict:
        data = self.get('/auth/me')
        self.csrf = None if self.api_token else data.get('csrfToken')
        self.user = data.get('user')
        return data

    def login(self, totp_code: str | None = None) -> dict:
        """Password login (+ TOTP). Raises QhhojError with the backend's code."""
        if self.api_token:
            return self.fetch_session()
        if not self.username or self.password is None:
            raise QhhojError('username/password required for session login')
        data = self.post('/auth/login', {'username': self.username,
                                         'password': self.password})
        self.csrf, self.user = data.get('csrfToken'), data.get('user')
        if data.get('twoFactorRequired'):
            code = totp_code or (totp(self.totp_secret) if self.totp_secret else None)
            if not code:
                raise QhhojError('two_factor_required: pass totp_secret/totp_code, '
                                 'or complete /login/2fa in a browser and reuse its cookie',
                                 code='two_factor_required')
            self.post('/auth/2fa/totp/verify', {'code': code})
            return self.fetch_session()
        if data.get('passwordChangeRequired'):
            raise QhhojError('password_change_required: POST /auth/password/change '
                             'first (breached password gate)',
                             code='password_change_required')
        return self.fetch_session()

    # ---------------- session / scope ----------------

    def me(self) -> dict:
        return self.get('/auth/me')

    def creation_organizations(self, kind: str = 'problem') -> list[dict]:
        """Organizations the account may create `kind` ('problem'|'contest') in."""
        return list(self.paged('/organizations', {'canCreate': kind}))

    # ---------------- problems ----------------

    def problem_meta(self) -> dict:
        return self.get('/problems/meta')

    def create_problem(self, code: str, name: str, time_limit: float,
                       memory_limit: int, points: float, type_ids: list,
                       group_id: Any, *, organization: str | None = None,
                       description: str | None = None, **extra) -> dict:
        body = {'code': code, 'name': name, 'timeLimit': time_limit,
                'memoryLimit': memory_limit, 'points': points,
                'typeIds': type_ids, 'groupId': group_id, **extra}
        if description is not None:
            body['description'] = description
        path = f'/organizations/{quote(organization)}/problems' if organization else '/problems'
        return self.post(path, body)

    def suggest_problem(self, body: dict) -> dict:
        return self.post('/problems/suggest', body)

    def get_problem(self, code: str, lang: str | None = None) -> dict:
        return self.get(f'/problems/{quote(code)}', params={'lang': lang} if lang else None)

    def patch_problem(self, code: str, **fields) -> dict:
        return self.patch(f'/problems/{quote(code)}', fields)

    def problem_id(self, code: str) -> str:
        """Resolve a problem code to its uuid (contest problem rows need the id)."""
        for row in self.paged('/problems', {'q': code, 'visibility': 'all'}):
            if row.get('code') == code:
                return row['id']
        raise QhhojError(f'problem {code!r} not found or not visible', code='not_found')

    # ---------------- test data ----------------

    def get_data(self, code: str) -> dict:
        return self.get(f'/problems/{quote(code)}/data')

    def upload_archive(self, code: str, zip_path: str) -> dict:
        p = Path(zip_path)
        return self.post(f'/problems/{quote(code)}/data/archive', file=(p.name, p.read_bytes()))

    def upload_data_file(self, code: str, kind: str, path: str) -> dict:
        p = Path(path)
        return self.post(f'/problems/{quote(code)}/data/files/{kind}',
                         file=(p.name, p.read_bytes()))

    def put_data(self, code: str, cases: list[dict], *, checker: str = 'standard',
                 grader: str = 'standard', checker_args: dict | None = None,
                 grader_args: dict | None = None, **flags) -> dict:
        body = {'checker': checker, 'grader': grader, 'cases': cases, **flags}
        if checker_args is not None:
            body['checkerArgs'] = checker_args
        if grader_args is not None:
            body['graderArgs'] = grader_args
        return self.put(f'/problems/{quote(code)}/data', body)

    # ---------------- Polygon imports ----------------

    def import_polygon_zip(self, zip_path: str, code: str, mode: str = 'create',
                           *, organization: str | None = None,
                           statement_languages: dict[str, str] | None = None,
                           **params) -> dict:
        """Returns {'jobId': …} — poll with poll_import(). Options travel in the query."""
        query: list[tuple[str, Any]] = [('code', code), ('mode', mode)]
        query += list(params.items())
        if organization:
            query.append(('organization', organization))
        for lang, target in (statement_languages or {}).items():
            query.append(('statementLanguages', f'{lang}={target}'))
        p = Path(zip_path)
        return self.request('POST', '/problems/imports', params=query,
                            file=(p.name, p.read_bytes()))

    def poll_import(self, job_id: str) -> dict:
        return self.get(f'/problems/imports/{quote(job_id)}')

    def wait_for_import(self, job_id: str, timeout: float = 900,
                        interval: float = 3.0) -> dict:
        def poll() -> dict:
            job = self.poll_import(job_id)
            job.setdefault('state', 'unknown')
            return job
        return _wait_job(poll, timeout, interval,
                         pending=('waiting', 'active', 'delayed', 'prioritized'))

    # ---------------- contests ----------------

    def create_contest(self, key: str, name: str, start: str, end: str, *,
                       organization: str | None = None, **extra) -> dict:
        body = {'key': key, 'name': name, 'startTime': start, 'endTime': end, **extra}
        path = f'/organizations/{quote(organization)}/contests' if organization else '/contests'
        return self.post(path, body)

    def get_contest(self, key: str) -> dict:
        return self.get(f'/contests/{quote(key)}')

    def patch_contest(self, key: str, **fields) -> dict:
        return self.patch(f'/contests/{quote(key)}', fields)

    def set_contest_problems(self, key: str, problems: list) -> dict:
        """problems: ready rows ({id, points, …}) or (problem_id_or_code, points)
        pairs — codes are resolved to ids. Sends the whole list (full replace)."""
        rows = []
        for item in problems:
            if isinstance(item, dict):
                rows.append(item)
                continue
            pid, points = item
            rows.append({'id': pid if _is_uuid(pid) else self.problem_id(pid),
                         'points': points})
        return self.patch_contest(key, problems=rows)

    def announce(self, key: str, title: str, description: str) -> dict:
        return self.post(f'/contests/{quote(key)}/announcements',
                         {'title': title, 'description': description})

    # ---------------- submissions ----------------

    def submit(self, code: str, source: str, language: str = '') -> dict:
        """language: language id (uuid) or key ('CPP17'). Returns {'id': …}."""
        return self.post(f'/problems/{quote(code)}/submit',
                         {'language': self._language_id(code, language),
                          'source': source})

    def submit_file(self, code: str, file_path: str, language: str = '') -> dict:
        """File-only languages: multipart with `language` field + one `file`."""
        lang_id = self._language_id(code, language, file_only=True)
        p = Path(file_path)
        return self.request('POST', f'/problems/{quote(code)}/submit/file',
                            form={'language': lang_id}, file=(p.name, p.read_bytes()))

    def _language_id(self, code: str, language: str, file_only: bool = False) -> str:
        if _is_uuid(language):
            return language
        for lang in self.get_problem(code).get('allowedLanguages', []):
            if lang.get('key') == language or lang.get('name') == language:
                if file_only and not lang.get('fileOnly'):
                    raise QhhojError(f'language {language!r} does not take files '
                                     '(use submit())', code='language_takes_text')
                return lang['id']
        raise QhhojError(f'language {language!r} not allowed on {code}',
                         code='language_not_allowed')

    def get_submission(self, submission_id: str) -> dict:
        return self.get(f'/submissions/{quote(submission_id)}')

    def wait_for_verdict(self, submission_id: str, timeout: float = 120,
                         interval: float = 2.0) -> dict:
        def poll() -> dict:
            s = self.get_submission(submission_id)
            s.setdefault('status', '')
            return s
        return _wait_job(poll, timeout, interval, pending=('queued', 'judging'))


def _wait_job(poll, timeout: float, interval: float, pending: tuple) -> dict:
    deadline = time.monotonic() + timeout
    while True:
        job = poll()
        if job.get('state', job.get('status')) not in pending:
            return job
        if time.monotonic() >= deadline:
            raise QhhojError(f'still {job.get("state") or job.get("status")} after '
                             f'{timeout}s (id={job.get("id")})', code='job_timeout')
        time.sleep(interval)


def _is_uuid(value: str) -> bool:
    try:
        return len(value) == 36 and int(value.replace('-', ''), 16) >= 0
    except (ValueError, AttributeError):
        return False


# ---------------- CLI probe ----------------

def _probe(client: QhhojClient) -> int:
    session = client.login()
    user = session.get('user') or {}
    print(f"signed in: {user.get('username')} (staff={user.get('isStaff')}, "
          f"superuser={user.get('isSuperuser')}, "
          f"permissions={len(user.get('permissions') or [])})")
    caps = user.get('adminCapabilities') or {}
    for kind in ('problemCreation', 'contestCreation'):
        scope = caps.get(kind) or {}
        print(f'{kind}: site={scope.get("site")} organizations={scope.get("organizations")}')
    if (caps.get('problemCreation') or {}).get('organizations'):
        for org in client.creation_organizations('problem'):
            print(f"  can create problems in: {org.get('slug')} ({org.get('name')})")
    if (caps.get('contestCreation') or {}).get('organizations'):
        for org in client.creation_organizations('contest'):
            print(f"  can create contests in: {org.get('slug')} ({org.get('name')})")
    rows, meta = client.get_page('/contests', page=1, page_size=5)
    for contest in rows:
        print(f"visible contest: {contest.get('key')} — {contest.get('name')}")
    print('API: OK (/api/internal answered)')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description='QHHOJ v2 client probe (read-only)')
    parser.add_argument('url')
    parser.add_argument('username', nargs='?')
    parser.add_argument('password', nargs='?')
    parser.add_argument('--totp', help='base32 TOTP secret')
    parser.add_argument('--token', help='API token (Bearer mode, no login)')
    args = parser.parse_args()
    if not args.token and (not args.username or args.password is None):
        parser.error('give url user pass [--totp S], or url --token T')
    try:
        client = QhhojClient(args.url, args.username, args.password,
                             totp_secret=args.totp, api_token=args.token)
        return _probe(client)
    except QhhojError as e:
        print(f'failed: [{e.code}] {e} (HTTP {e.status})', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
