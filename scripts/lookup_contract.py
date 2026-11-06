#!/usr/bin/env python3
"""Read-only lookup into references/contracts.json (the skill's OpenAPI subset).

Usage:
  lookup_contract.py METHOD /path        # one operation + every schema it references
  lookup_contract.py list [substring]    # list operations (optionally filtered), with summaries

Paths are templates: /problems/{code}/data, /contests/{key}, /organizations/{slug}.
A leading /api/internal is optional and added for you. METHOD is case-insensitive.

The printed operation carries the backend's own description: permission codenames,
quotas, rate limits and error codes. Read it before building the request.
"""
import argparse
import json
import re
import sys
from pathlib import Path

try:  # piping into `head` should not raise
    import signal
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except (AttributeError, ValueError):  # non-POSIX platforms
    pass

CONTRACTS = Path(__file__).resolve().parents[1] / 'references' / 'contracts.json'
METHODS = ('get', 'post', 'put', 'patch', 'delete')


def load():
    try:
        return json.loads(CONTRACTS.read_text())
    except FileNotFoundError:
        sys.exit(f'contracts.json not found at {CONTRACTS}')


def normalize(path):
    path = '/' + path.strip('/')
    if not path.startswith('/api/internal/'):
        path = '/api/internal/' + path.lstrip('/')
    return path


def show_operation(spec, method, path):
    operation = spec.get('paths', {}).get(path, {}).get(method.lower())
    if operation is None:
        near = [p for p in spec.get('paths', {}) if p.rsplit('/', 1)[-1] == path.rsplit('/', 1)[-1]]
        hint = f' Near-misses in the snapshot: {near}.' if near else ''
        sys.exit(f'Operation {method.upper()} {path} is absent from the snapshot. '
                 f'Use a template path and check references/api.md.{hint}')
    found = {}

    def visit(obj):
        if isinstance(obj, dict):
            ref = obj.get('$ref', '')
            if ref.startswith('#/components/schemas/'):
                name = ref.rsplit('/', 1)[1]
                if name not in found:
                    found[name] = spec['components']['schemas'][name]
                    visit(found[name])
            for value in obj.values():
                visit(value)
        elif isinstance(obj, list):
            for value in obj:
                visit(value)

    visit(operation)
    print(json.dumps({'method': method.upper(), 'path': path,
                      'operation': operation, 'schemas': found},
                     ensure_ascii=False, indent=2))


def list_operations(spec, pattern):
    rx = re.compile(re.escape(pattern), re.I) if pattern else None
    for path, methods in sorted(spec.get('paths', {}).items()):
        for method, op in sorted(methods.items()):
            if method not in METHODS:
                continue
            summary = op.get('summary', '')
            if rx and not (rx.search(path) or rx.search(summary) or rx.search(method)):
                continue
            print(f'{method.upper():7} {path}  — {summary}')


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('method', help='HTTP method, or "list"')
    parser.add_argument('path', nargs='?', default='', help='template path (or substring filter for "list")')
    args = parser.parse_args()

    spec = load()
    if args.method.lower() == 'list':
        list_operations(spec, args.path)
        return
    if args.method.lower() not in METHODS:
        sys.exit('METHOD must be one of GET/POST/PUT/PATCH/DELETE, or "list".')
    if not args.path:
        sys.exit('A path is required, e.g. /problems/{code}/data')
    show_operation(spec, args.method, normalize(args.path))


if __name__ == '__main__':
    main()
