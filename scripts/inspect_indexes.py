#!/usr/bin/env python3
"""Inspect a local SQLite snapshot read-only; never emit executable DROP statements."""
import json
import sqlite3
import sys
from pathlib import Path


def quote_identifier(name):
    return '"' + name.replace('"', '""') + '"'


def inspect(path):
    path = Path(path).resolve(strict=True)
    if not path.is_file():
        raise ValueError('Expected an existing SQLite snapshot file')
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    try:
        db.execute('PRAGMA query_only=ON')
        inventory = []
        for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
            table = row['name']
            for index in db.execute('PRAGMA index_list(' + quote_identifier(table) + ')'):
                terms = [dict(term) for term in db.execute(
                    'PRAGMA index_xinfo(' + quote_identifier(index['name']) + ')') if term['key']]
                inventory.append({
                    'table': table, 'name': index['name'], 'unique': bool(index['unique']),
                    'partial': bool(index['partial']), 'origin': index['origin'],
                    'terms': [{'column': term['name'], 'cid': term['cid'],
                               'descending': bool(term['desc']), 'collation': term['coll']}
                              for term in terms],
                })
        candidates = []
        for short in inventory:
            if short['unique'] or short['partial'] or short['origin'] != 'c':
                continue
            if not short['terms'] or any(term['cid'] < 0 for term in short['terms']):
                continue
            for long in inventory:
                if long['table'] != short['table'] or long['partial'] or long['name'] == short['name']:
                    continue
                if any(term['cid'] < 0 for term in long['terms']):
                    continue
                if len(long['terms']) < len(short['terms']):
                    continue
                if long['terms'][:len(short['terms'])] == short['terms']:
                    candidates.append({'table': short['table'], 'candidate': short['name'],
                                       'covered_prefix_by': long['name']})
        return {'mode': 'read-only schema inspection', 'indexes': inventory,
                'candidates': candidates,
                'warning': 'Candidates only. Validate workload, ordering, constraints and D1 costs. '
                           'Do not drop every candidate: identical indexes can cover each other.'}
    finally:
        db.close()


if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise ValueError('Usage: inspect_indexes.py existing-local-snapshot.sqlite')
        print(json.dumps(inspect(sys.argv[1]), indent=2))
    except (ValueError, OSError, sqlite3.Error) as error:
        print('Index inspection failed: ' + str(error), file=sys.stderr)
        sys.exit(1)
