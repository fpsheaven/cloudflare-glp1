#!/usr/bin/env python3
"""Bounded Cloudflare read-only collection. No arbitrary SQL, URLs or credential discovery."""
import argparse
import hashlib
import json
import math
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler


BASE = 'https://api.cloudflare.com/client/v4/'
SCHEMA = "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE type IN ('table','index','trigger') ORDER BY type,name LIMIT 1000"


def stamp():
    return datetime.now(timezone.utc).isoformat()


def plan(config):
    allowed = {'account_id', 'start_date', 'end_date_exclusive', 'database_ids', 'workers'}
    if set(config) - allowed:
        raise ValueError('Unsupported config fields; credentials belong in the environment only')
    account = config['account_id']
    if not re.fullmatch(r'[0-9a-f]{32}', account):
        raise ValueError('Invalid account ID')
    start = datetime.strptime(config['start_date'], '%Y-%m-%d').replace(tzinfo=timezone.utc)
    end = datetime.strptime(config['end_date_exclusive'], '%Y-%m-%d').replace(tzinfo=timezone.utc)
    if not 0 < (end - start).days <= 31 or end > datetime.now(timezone.utc):
        raise ValueError('Use 1–31 complete UTC days, with an exclusive end date')
    databases, workers = config.get('database_ids', []), config.get('workers', [])
    if not isinstance(databases, list) or not isinstance(workers, list):
        raise ValueError('Resource selections must be lists')
    if len(databases) + len(workers) > 20 or not databases and not workers:
        raise ValueError('Select 1–20 explicit resources')
    if len(set(databases)) != len(databases) or len(set(workers)) != len(workers):
        raise ValueError('Duplicate resource')
    requests = []
    for db in databases:
        if not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', db):
            raise ValueError('Invalid database ID')
        query = '''query { viewer { accounts(filter:{accountTag:"%s"}) {
          d1AnalyticsAdaptiveGroups(limit:100,filter:{databaseId:"%s",date_geq:"%s",date_leq:"%s"},orderBy:[date_ASC]) {
          dimensions {date databaseId} sum {rowsRead rowsWritten readQueries writeQueries} } } } }''' % (
            account, db, start.date(), (end - timedelta(days=1)).date())
        requests.extend([
            {'id': 'd1-' + db + '-usage', 'path': 'graphql', 'body': {'query': query}, 'kind': 'usage'},
            {'id': 'd1-' + db + '-schema', 'path': f'accounts/{account}/d1/database/{db}/query',
             'body': {'sql': SCHEMA}, 'kind': 'schema'},
        ])
    for worker in workers:
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,63}', worker):
            raise ValueError('Invalid Worker name')
        for endpoint in ('deployments', 'schedules'):
            requests.append({'id': 'worker-' + worker + '-' + endpoint,
                             'path': f'accounts/{account}/workers/scripts/{worker}/{endpoint}', 'kind': endpoint})
        query = '''query { viewer { accounts(filter:{accountTag:"%s"}) {
          workersInvocationsAdaptive(limit:100,filter:{scriptName:"%s",datetime_geq:"%s",datetime_lt:"%s"}) {
          dimensions {scriptName status} sum {requests errors subrequests} } } } }''' % (
            account, worker, start.isoformat(), end.isoformat())
        requests.append({'id': 'worker-' + worker + '-usage', 'path': 'graphql', 'body': {'query': query}, 'kind': 'worker_usage'})
    return requests


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(item, token):
    body = json.dumps(item['body']).encode() if 'body' in item else None
    request = Request(BASE + item['path'], data=body,
                      headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    try:
        with build_opener(NoRedirect()).open(request, timeout=30) as response:
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            return {'error': 'response_size_limit'}
        result = json.loads(raw)
        if not isinstance(result, dict):
            return {'error': 'invalid_response_shape'}
        if result.get('errors') or result.get('success') is False:
            return {'error': 'provider_error_or_permission_or_schema_gap'}
        return {'value': result}
    except HTTPError as error:
        return {'error': 'http_' + str(error.code)}
    except (URLError, TimeoutError, OSError, ValueError):
        return {'error': 'network_or_invalid_response'}


def sanitize(kind, value):
    """Persist selected fields only; deployments can otherwise contain email/annotations."""
    if kind in ('usage', 'worker_usage'):
        accounts = value['data']['viewer']['accounts']
        if len(accounts) != 1:
            raise ValueError('Account scope unavailable')
        field = 'd1AnalyticsAdaptiveGroups' if kind == 'usage' else 'workersInvocationsAdaptive'
        rows = accounts[0][field]
        allowed_dims = ('date', 'databaseId') if kind == 'usage' else ('scriptName', 'status')
        allowed_sums = ('rowsRead', 'rowsWritten', 'readQueries', 'writeQueries') if kind == 'usage' else ('requests', 'errors', 'subrequests')
        for row in rows:
            for key in allowed_sums:
                quantity = row['sum'][key]
                if isinstance(quantity, bool) or not isinstance(quantity, (int, float)) or not math.isfinite(quantity) or quantity < 0:
                    raise ValueError('Missing or invalid metric; do not infer zero')
        return {'rows': [{'dimensions': {k: r['dimensions'][k] for k in allowed_dims},
                          'sum': {k: r['sum'][k] for k in allowed_sums}} for r in rows],
                'possibly_truncated': len(rows) >= 100}
    if kind == 'schema':
        result = value['result'][0]
        if not isinstance(result, dict) or result.get('success') is not True:
            raise ValueError('D1 query failed')
        return {'rows': [{k: r[k] for k in ('type', 'name', 'tbl_name', 'sql')} for r in result['results']],
                'possibly_truncated': len(result['results']) >= 1000,
                'meta': {k: result.get('meta', {}).get(k) for k in ('rows_read', 'rows_written', 'duration')}}
    result = value['result']
    if kind == 'deployments':
        return {'rows': [{k: r[k] for k in ('id', 'created_on', 'versions')} for r in result['deployments']],
                'coverage': 'Returned deployment history only; not a full configuration snapshot'}
    return {'rows': [{k: r.get(k) for k in ('cron', 'created_on', 'modified_on')} for r in result['schedules']]}


def collect(config, directory, transport):
    requests = plan(config)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    receipt = {'schema_version': 1, 'collected_at': stamp(), 'scope': config, 'datasets': [],
               'gaps': ['Invoices, account allowances, CPU distributions, logs, other products and external-provider meters require separate evidence.',
                        'A complete day may still be awaiting analytics ingestion. Schema can contain sensitive defaults; keep this bundle private.']}
    for item in requests:
        record = {'id': item['id'], 'kind': item['kind'], 'retrieved_at': stamp()}
        response = transport(item)
        try:
            if 'error' in response:
                raise ValueError(response['error'])
            data = sanitize(item['kind'], response['value'])
            raw = json.dumps(data, indent=2).encode()
            filename = item['id'] + '.json'
            (directory / filename).write_bytes(raw)
            record.update(status='collected', file=filename, sha256=hashlib.sha256(raw).hexdigest())
            if not data['rows']:
                record['gap'] = 'No rows returned; do not infer zero usage or absent configuration without confirmation'
            if data.get('possibly_truncated'):
                record['gap'] = 'Dataset cap reached; split the window or collect through another bounded method'
            if item['kind'] == 'usage':
                dates = {r['dimensions']['date'] for r in data['rows']}
                expected = (datetime.fromisoformat(config['end_date_exclusive']) - datetime.fromisoformat(config['start_date'])).days
                if len(dates) != expected:
                    record['gap'] = 'Missing UTC days; zero traffic, retention, ingestion and collection gaps are unresolved'
        except (ValueError, KeyError, TypeError, IndexError):
            record.update(status='unavailable', gap=response.get('error', 'Unexpected provider response shape'))
        receipt['datasets'].append(record)
    (directory / 'manifest.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--live', action='store_true', help='Execute the printed fixed read-only request plan')
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text(encoding='utf-8-sig'))
        if not args.live:
            print(json.dumps({'requests': plan(config), 'status': 'dry-run; no network requests'}, indent=2))
        else:
            token = os.environ.get('CLOUDFLARE_API_TOKEN')
            if not token or not args.output:
                raise ValueError('Set CLOUDFLARE_API_TOKEN and a new --output directory')
            result = collect(config, args.output, lambda item: fetch(item, token))
            print(json.dumps({'manifest': str(args.output / 'manifest.json'),
                              'unavailable': sum(d['status'] != 'collected' for d in result['datasets'])}))
    except (ValueError, KeyError, TypeError, OSError):
        parser.exit(2, 'Collection failed; check config, environment credential and new output path. No credential values are printed.\n')
