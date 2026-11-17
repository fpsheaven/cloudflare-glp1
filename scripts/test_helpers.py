#!/usr/bin/env python3
import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from estimate_cost import estimate
from inspect_indexes import inspect


def scenario(**changes):
    return dict(meter='synthetic writes', currency='USD', observed_seconds=86400,
                target_seconds=2592000, baseline_units=4000000, candidate_units=2500000,
                included_units=50000000, price_unit_size=1000000, price_per_unit=1, **changes)


class CostTests(unittest.TestCase):
    def test_shared_allowance_crossing(self):
        value = scenario()
        value['candidate_units'] = 1000000
        result = estimate(value)
        self.assertEqual(result['baseline']['overage_cost'], '70')
        self.assertEqual(result['candidate']['overage_cost'], '0')
        self.assertEqual(result['modeled_savings'], '70')

    def test_both_over_allowance(self):
        self.assertEqual(estimate(scenario())['modeled_savings'], '45')

    def test_bad_values(self):
        for field, value in [('observed_seconds', 0), ('target_seconds', -1),
                             ('baseline_units', True), ('candidate_units', 'NaN'),
                             ('price_per_unit', 'Infinity'), ('price_unit_size', 0)]:
            with self.subTest(field=field):
                data = scenario()
                data[field] = value
                with self.assertRaises(ValueError):
                    estimate(data)

    def test_short_sample_and_regression(self):
        data = scenario()
        data.update(observed_seconds=60, candidate_units=5000000)
        result = estimate(data)
        self.assertTrue(result['modeled_savings'].startswith('-'))
        self.assertTrue(any('shorter' in warning for warning in result['warnings']))


class IndexTests(unittest.TestCase):
    def test_candidates_preserve_constraints_and_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.sqlite'
            db = sqlite3.connect(path)
            db.executescript('''
                CREATE TABLE events(id INTEGER PRIMARY KEY, owner TEXT, created INTEGER);
                CREATE INDEX narrow ON events(owner);
                CREATE INDEX covering ON events(owner,created);
                CREATE UNIQUE INDEX unique_owner ON events(owner);
                CREATE INDEX partial_owner ON events(owner) WHERE created>0;
                CREATE INDEX reverse_owner ON events(owner DESC);
                CREATE INDEX nocase_owner ON events(owner COLLATE NOCASE);
                CREATE INDEX expression_owner ON events(lower(owner));
                CREATE INDEX "quoted""name" ON events(created);
                INSERT INTO events(owner,created) VALUES('synthetic',1);
            ''')
            db.close()
            before = hashlib.sha256(path.read_bytes()).digest()
            report = inspect(path)
            self.assertEqual(before, hashlib.sha256(path.read_bytes()).digest())
            pairs = {(row['candidate'], row['covered_prefix_by']) for row in report['candidates']}
            self.assertIn(('narrow', 'covering'), pairs)
            forbidden = {'unique_owner', 'partial_owner', 'reverse_owner', 'nocase_owner', 'expression_owner'}
            self.assertFalse(any(name in forbidden for name, _ in pairs))

    def test_missing_file_is_not_created(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'missing.sqlite'
            with self.assertRaises(FileNotFoundError):
                inspect(path)
            self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
