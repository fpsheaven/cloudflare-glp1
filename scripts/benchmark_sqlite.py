#!/usr/bin/env python3
"""Matched, synthetic, in-memory SQLite benchmark and data-equivalence check."""
import argparse
import hashlib
import json
import platform
import sqlite3
import statistics
import time
from pathlib import Path

from audit_models import unique


def digest(value, ordered=True):
    rows = [json.dumps(row, sort_keys=True, separators=(',', ':'), default=lambda x: {'bytes': x.hex()}) for row in value]
    if not ordered:
        rows.sort()
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()


def authorizer(action, arg1, arg2, database, trigger):
    if action in (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH, sqlite3.SQLITE_PRAGMA):
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_FUNCTION and (arg2 or '').lower() in ('load_extension', 'readfile', 'writefile'):
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def snapshot(db, tables):
    result = {}
    for name in tables:
        quoted = '"' + name.replace('"', '""') + '"'
        rows = db.execute('SELECT * FROM ' + quoted + ' LIMIT 50001').fetchall()
        if len(rows) > 50000:
            raise ValueError('Synthetic fixture table exceeds 50,000 rows')
        result[name] = digest(rows, ordered=False)
    return result


def run_variant(case, variant):
    db = sqlite3.connect(':memory:', isolation_level=None)
    db.execute('PRAGMA temp_store=MEMORY')
    db.set_authorizer(authorizer)
    counter = [0]

    def progress():
        counter[0] += 1
        return int(counter[0] > 2_000_000)

    db.set_progress_handler(progress, 1)
    try:
        db.executescript(case['schema'] + '\n' + case['seed'])
        counter[0] = 0
        db.executescript(case.get(variant + '_setup', ''))
        counter[0] = 0
        initial = snapshot(db, case['preserve_tables'])
        output = []
        for step in case['steps']:
            commands = step.get(variant, step.get('commands'))
            if not commands or len(commands) > 100:
                raise ValueError('Each step needs 1–100 SQL commands')
            plans = []
            for command in commands:
                sql = command['sql']
                if sql.lstrip().upper().startswith(('SELECT ', 'WITH ')):
                    counter[0] = 0
                    plans.append(db.execute('EXPLAIN QUERY PLAN ' + sql, command.get('params', [])).fetchall())
            counter[0] = 0
            before = db.total_changes
            started = time.perf_counter()
            results, error = [], None
            db.execute('BEGIN')
            try:
                for command in commands:
                    cursor = db.execute(command['sql'], command.get('params', []))
                    rows = cursor.fetchmany(50001) if cursor.description else []
                    if len(rows) > 50000:
                        raise ValueError('Result exceeds synthetic benchmark bound')
                    results.append({'columns': [d[0] for d in cursor.description] if cursor.description else [],
                                    'hash': digest(rows, ordered=step.get('ordered', True)), 'count': len(rows)})
                db.execute('COMMIT')
            except sqlite3.Error as exception:
                error = exception.sqlite_errorcode
                db.set_progress_handler(None, 0)
                if db.in_transaction:
                    db.execute('ROLLBACK')
            elapsed = (time.perf_counter() - started) * 1000
            vm_steps = counter[0]
            db.set_progress_handler(None, 0)
            changed = db.total_changes - before
            state = snapshot(db, case['preserve_tables'])
            expected = step.get('expect_error')
            acceptable = error == expected
            if error == sqlite3.SQLITE_INTERRUPT:
                raise ValueError('VM instruction budget exceeded')
            output.append({'id': case['id'] + '/' + step['id'],
                           'signature': {'results': results, 'error': error, 'state': state},
                           'expected_outcome': acceptable, 'plans': plans,
                           'metrics': {'latency_ms': elapsed, 'vm_steps': vm_steps, 'sqlite_changes': changed}})
            counter[0] = 0
            db.set_progress_handler(progress, 1)
        return initial, output
    finally:
        db.close()


def benchmark(data):
    unique(data['cases'], 'id')
    repetitions = data.get('repetitions', 3)
    if isinstance(repetitions, bool) or not isinstance(repetitions, int) or not 1 <= repetitions <= 10:
        raise ValueError('Repetitions must be 1–10')
    if not 1 <= len(data['cases']) <= 30:
        raise ValueError('Supply 1–30 synthetic cases')
    for case in data['cases']:
        unique(case['steps'], 'id')
        if not case['preserve_tables'] or not 1 <= len(case['steps']) <= 100:
            raise ValueError('Preserved tables and 1–100 steps are required')
    fixture = {k: data[k] for k in ('cases', 'repetitions') if k in data}
    fingerprint = hashlib.sha256(json.dumps(fixture, sort_keys=True).encode()).hexdigest()
    env = {'engine': 'sqlite', 'engine_version': sqlite3.sqlite_version, 'python': platform.python_version(),
           'platform': platform.platform(), 'cache_mode': 'fresh in-memory DB per repetition; later steps may be warm'}
    results = {v: {'fixture_sha256': fingerprint, 'environment': env, 'observations': []} for v in ('baseline', 'candidate')}
    mismatches = []
    for case in data['cases']:
        runs = {v: [] for v in results}
        for repetition in range(repetitions):
            order = ('baseline', 'candidate') if repetition % 2 == 0 else ('candidate', 'baseline')
            initials = {}
            for variant in order:
                initials[variant], observations = run_variant(case, variant)
                runs[variant].append(observations)
            if initials['baseline'] != initials['candidate']:
                mismatches.append(case['id'] + ':setup changed retained data')
            for left, right in zip(runs['baseline'][-1], runs['candidate'][-1]):
                if left['signature'] != right['signature'] or not left['expected_outcome'] or not right['expected_outcome']:
                    mismatches.append(left['id'])
        for variant in results:
            for i, observation in enumerate(runs[variant][0]):
                if any(r[i]['signature'] != observation['signature'] for r in runs[variant]):
                    mismatches.append(observation['id'] + ':nondeterministic')
                entry = dict(observation)
                entry['metrics'] = {key: statistics.median(r[i]['metrics'][key] for r in runs[variant]) for key in observation['metrics']}
                results[variant]['observations'].append(entry)
    return {**results, 'equivalent': not mismatches, 'mismatches': sorted(set(mismatches)),
            'limitations': ['Synthetic SQLite only: VM steps and total_changes are NOT D1 billed rows or Worker CPU.',
                           'Each step is a transaction. Rolled-back writes may still appear in sqlite_changes.',
                           'No network, true concurrent clients, persistent-disk cold cache, application timers or delivery guarantees are tested.',
                           'Use actual Workerd/engine and application tests for those guarantees.'],
            'rules': data.get('rules', [])}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture', type=Path)
    parser.add_argument('--output', type=Path, help='Write UTF-8 JSON to a new file; never overwrite evidence')
    args = parser.parse_args()
    try:
        if args.fixture.stat().st_size > 2_000_000:
            raise ValueError('Fixture file too large')
        result = benchmark(json.loads(args.fixture.read_text(encoding='utf-8-sig')))
        encoded = json.dumps(result, indent=2)
        if args.output:
            with args.output.open('x', encoding='utf-8') as output:
                output.write(encoded)
        else:
            print(encoded)
        if not result['equivalent']:
            raise SystemExit(1)
    except (ValueError, KeyError, TypeError, sqlite3.Error, OSError):
        parser.exit(2, 'Benchmark input/execution failed; check fixture schema, bounds and SQL.\n')
