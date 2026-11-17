#!/usr/bin/env python3
import copy
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from audit_models import forecast, regression, timeline, score, reconcile
from benchmark_sqlite import benchmark
from collect_evidence import plan, collect, sanitize

ROOT = Path(__file__).resolve().parents[1]


def example(name):
    return json.loads((ROOT / 'examples' / (name + '.json')).read_text())


class ModelTests(unittest.TestCase):
    def test_unexplained_and_overlapping_costs(self):
        data = {'currency': 'USD', 'period': 'same month', 'total_cost': 100,
                'attributed': [{'id': 'db', 'cost': 60}]}
        self.assertEqual(reconcile(data)['unexplained_cost'], '40')
        data['attributed'].append({'id': 'other', 'cost': 80})
        self.assertIn('over-attributed', reconcile(data)['status'])
    def test_growth_allowances_and_added_writes(self):
        result = forecast(example('growth'))['scenarios']
        self.assertEqual(result[0]['baseline_cost'], '6.8')
        self.assertEqual(result[0]['candidate_cost'], '5.24')
        self.assertEqual(result[0]['recurring_saving'], '1.56')
        self.assertEqual(result[0]['first_period_saving'], '-0.44')
        self.assertGreater(float(result[2]['recurring_saving']), float(result[1]['recurring_saving']))

    def test_no_payback_and_invalid_meter(self):
        data = example('growth')
        data['fixed_cost']['candidate'] = 100000
        self.assertIsNone(forecast(data)['scenarios'][0]['payback_periods'])
        data['meters'].append(copy.deepcopy(data['meters'][0]))
        with self.assertRaises(ValueError):
            forecast(data)

    def test_bad_numbers_and_missing_drivers(self):
        for value in [True, -1, 'NaN', 'Infinity']:
            data = example('growth')
            data['migration_cost'] = value
            with self.assertRaises(ValueError):
                forecast(data)
        data = example('growth')
        del data['scenarios'][0]['factors']['history']
        with self.assertRaises(KeyError):
            forecast(data)

    def test_timeline_detects_traffic_confounding(self):
        event = timeline(example('timeline'))['events'][0]
        self.assertEqual(event['before']['units_per_success']['rows_read'], '100')
        self.assertEqual(event['after']['units_per_success']['rows_read'], '100')
        self.assertEqual(event['after']['errors'], '50')
        self.assertIn('traffic-shift', event['nearby_events'])
        self.assertTrue(event['before']['complete_window'])

    def test_timeline_gaps_zero_and_overlap(self):
        data = example('timeline')
        data['buckets'][1]['successful_actions'] = 0
        self.assertIsNone(timeline(data)['events'][0]['after']['units_per_success']['rows_read'])
        data['buckets'] = data['buckets'][:1]
        self.assertFalse(timeline(data)['events'][0]['after']['complete_window'])
        data['buckets'].append(copy.deepcopy(data['buckets'][0]))
        with self.assertRaises(ValueError):
            timeline(data)

    def test_score_false_positives_and_unsafe_actions(self):
        result = score({'cases': [{'id': 'one', 'expected': ['a', 'b'], 'reported': ['a', 'fake'],
                                  'unsafe_actions': ['delete'], 'unsupported_savings': ['claim'], 'has_improvement_list': False}]})
        self.assertEqual(result['precision'], 0.5)
        self.assertEqual(result['recall'], 0.5)
        self.assertEqual(result['unsafe_actions'], 1)
        self.assertEqual(result['missing_improvement_lists'], 1)


class BenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = example('sqlite-workload')
        cls.data['repetitions'] = 1
        cls.result = benchmark(cls.data)

    def test_index_semantics_failures_and_recovery(self):
        self.assertTrue(self.result['equivalent'], self.result['mismatches'])
        self.assertTrue(regression(self.result)['passed'])
        observed = self.result['baseline']['observations']
        self.assertEqual(observed[-2]['signature']['error'], sqlite3.SQLITE_CONSTRAINT_PRIMARYKEY)
        self.assertEqual(observed[-3]['signature']['state'], observed[-2]['signature']['state'])

    def test_detects_lost_data_and_changed_query(self):
        data = copy.deepcopy(self.data)
        data['cases'][0]['candidate_setup'] += ' DELETE FROM events WHERE id=1;'
        self.assertFalse(benchmark(data)['equivalent'])
        data = copy.deepcopy(self.data)
        data['cases'][0]['steps'][0]['candidate'] = [{'sql': 'SELECT id,created,value FROM events WHERE 0 ORDER BY id'}]
        self.assertFalse(benchmark(data)['equivalent'])

    def test_unsafe_local_file_access_denied(self):
        data = copy.deepcopy(self.data)
        data['cases'][0]['candidate_setup'] = "ATTACH DATABASE ':memory:' AS other;"
        with self.assertRaises(sqlite3.DatabaseError):
            benchmark(data)

    def test_regression_failure_missing_and_mismatched_metrics(self):
        data = copy.deepcopy(self.result)
        data['rules'][0]['max_ratio'] = 0
        self.assertFalse(regression(data)['passed'])
        data['candidate']['fixture_sha256'] = 'other'
        with self.assertRaises(ValueError):
            regression(data)
        data = copy.deepcopy(self.result)
        del data['candidate']['observations'][0]['metrics']['vm_steps']
        with self.assertRaises(KeyError):
            regression(data)


class CollectorTests(unittest.TestCase):
    def test_plan_is_fixed_and_dates_bounded(self):
        data = example('collection')
        requests = plan(data)
        self.assertEqual(len(requests), 5)
        self.assertTrue(all(r['path'].startswith(('accounts/', 'graphql')) for r in requests))
        self.assertTrue(all('body' not in r or 'query' in r['body'] or r['body']['sql'].startswith('SELECT type,name') for r in requests))
        data['workers'] = ['../../evil']
        with self.assertRaises(ValueError):
            plan(data)
        data = example('collection')
        data['token'] = 'should-not-be-stored'
        with self.assertRaises(ValueError):
            plan(data)

    def test_permission_gaps_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'bundle'
            result = collect(example('collection'), path, lambda item: {'error': 'http_403'})
            self.assertEqual(len(result['datasets']), 5)
            self.assertTrue(all(r['status'] == 'unavailable' for r in result['datasets']))
            with self.assertRaises(FileExistsError):
                collect(example('collection'), path, lambda item: {})

    def test_null_metrics_are_unavailable_not_zero(self):
        with tempfile.TemporaryDirectory() as root:
            data = example('collection')
            data['workers'] = []
            def response(item):
                if item['kind'] != 'usage':
                    return {'error': 'http_403'}
                return {'value': {'data': {'viewer': {'accounts': [{'d1AnalyticsAdaptiveGroups': [
                    {'dimensions': {'date': '2026-01-01', 'databaseId': data['database_ids'][0]},
                     'sum': {'rowsRead': None, 'rowsWritten': 0, 'readQueries': 0, 'writeQueries': 0}}
                ]}]}}}}
            result = collect(data, Path(root) / 'bundle', response)
            self.assertEqual(result['datasets'][0]['status'], 'unavailable')

    def test_sanitized_deployment_and_empty_usage(self):
        schedule = sanitize('schedules', {'result': {'schedules': [{'cron': '0 0 * * *'}]}})
        self.assertEqual(schedule['rows'][0]['cron'], '0 0 * * *')
        value = {'result': {'deployments': [{'id': 'v', 'created_on': 'now', 'versions': [],
                                             'author_email': 'private', 'annotations': {'secret': 'hidden'}}]}}
        self.assertNotIn('private', json.dumps(sanitize('deployments', value)))
        self.assertNotIn('hidden', json.dumps(sanitize('deployments', value)))
        with tempfile.TemporaryDirectory() as root:
            data = example('collection')
            data['workers'] = []
            def response(item):
                if item['kind'] == 'usage':
                    return {'value': {'data': {'viewer': {'accounts': [{'d1AnalyticsAdaptiveGroups': []}]}}}}
                return {'error': 'http_403'}
            result = collect(data, Path(root) / 'bundle', response)
            self.assertIn('gap', result['datasets'][0])


class CLITests(unittest.TestCase):
    def call(self, script, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts' / script), *map(str, args)],
                              capture_output=True, text=True, timeout=30)

    def test_benchmark_gate_and_evidence_no_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            output = Path(root) / 'benchmark.json'
            run = self.call('benchmark_sqlite.py', ROOT / 'examples/sqlite-workload.json', '--output', output)
            self.assertEqual(run.returncode, 0, run.stderr)
            gate = self.call('audit_models.py', 'regression', output)
            self.assertEqual(gate.returncode, 0, gate.stderr)
            self.assertTrue(json.loads(gate.stdout)['passed'])
            again = self.call('benchmark_sqlite.py', ROOT / 'examples/sqlite-workload.json', '--output', output)
            self.assertEqual(again.returncode, 2)
            data = json.loads(output.read_text())
            data['rules'][0]['max_ratio'] = 0
            output.write_text(json.dumps(data))
            self.assertEqual(self.call('audit_models.py', 'regression', output).returncode, 1)

    def test_offline_examples_and_missing_evidence_exit(self):
        for mode, name in [('forecast', 'growth'), ('timeline', 'timeline')]:
            result = self.call('audit_models.py', mode, ROOT / 'examples' / (name + '.json'))
            self.assertEqual(result.returncode, 0, result.stderr)
            json.loads(result.stdout)
        dry = self.call('collect_evidence.py', ROOT / 'examples/collection.json')
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertEqual(json.loads(dry.stdout)['status'], 'dry-run; no network requests')
        self.assertEqual(self.call('audit_models.py', 'regression', ROOT / 'examples/growth.json').returncode, 2)


if __name__ == '__main__':
    unittest.main()
