#!/usr/bin/env python3
"""Offline forecast, regression gates, timeline analysis and evaluation scoring."""
import argparse
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path


def number(value):
    if isinstance(value, bool):
        raise ValueError('Boolean is not a measurement')
    value = Decimal(str(value))
    if not value.is_finite() or value < 0:
        raise ValueError('Expected a finite nonnegative number')
    return value


def unique(items, key):
    keys = [item[key] for item in items]
    if len(set(keys)) != len(keys) or any(not isinstance(k, str) or not k for k in keys):
        raise ValueError('IDs must be nonempty and unique: ' + key)


def forecast(data):
    unique(data['meters'], 'id')
    unique(data['scenarios'], 'id')
    if not data['currency'] or not data['period'] or not data['meters'] or not data['scenarios']:
        raise ValueError('Currency, period, meters and scenarios are required')
    output = []
    for scenario in data['scenarios']:
        factors = {k: number(v) for k, v in scenario['factors'].items()}
        totals = {v: number(data['fixed_cost'][v]) for v in ('baseline', 'candidate')}
        meters = []
        for meter in data['meters']:
            if meter.get('pricing') != 'linear':
                raise ValueError('Only explicitly linear pricing is supported')
            unit = number(meter['price_unit_size'])
            if unit == 0:
                raise ValueError('Price unit size must be positive')
            values = {}
            for variant in totals:
                units = number(meter['other_account_units'])
                for term in meter[variant]:
                    volume = number(term['units'])
                    for driver, power in term.get('drivers', {}).items():
                        if not isinstance(power, int) or isinstance(power, bool) or not 0 <= power <= 4:
                            raise ValueError('Growth powers must be integers from 0 to 4')
                        volume *= factors[driver] ** power
                    units += volume
                cost = max(Decimal(0), units - number(meter['allowance'])) / unit * number(meter['price'])
                values[variant] = {'units': str(units), 'cost': str(cost)}
                totals[variant] += cost
            meters.append({'id': meter['id'], **values})
        saving = totals['baseline'] - totals['candidate']
        migration = number(data['migration_cost'])
        output.append({'id': scenario['id'], 'meters': meters,
                       'baseline_cost': str(totals['baseline']), 'candidate_cost': str(totals['candidate']),
                       'recurring_saving': str(saving), 'first_period_saving': str(saving - migration),
                       'payback_periods': str(migration / saving) if saving > 0 else None})
    return {'currency': data['currency'], 'period': data['period'], 'scenarios': output,
            'limitations': ['Inputs must already cover the same complete billing period.',
                           'One entry per independently billed allowance pool; combine overlapping fixes before modeling.',
                           'Other-account usage is held constant; tiers, rounding, tax and nonlinear pricing are unsupported.',
                           'Growth factors are assumptions, not measured forecasts.']}


def regression(data):
    base, candidate = data['baseline'], data['candidate']
    for field in ('fixture_sha256', 'environment'):
        if base[field] != candidate[field]:
            raise ValueError('Unmatched benchmark ' + field)
    if not data['rules']:
        raise ValueError('At least one explicit regression threshold is required')
    if data.get('equivalent') is not True:
        return {'passed': False, 'failures': ['Data/result equivalence was not established']}
    unique(base['observations'], 'id')
    unique(candidate['observations'], 'id')
    left = {x['id']: x for x in base['observations']}
    right = {x['id']: x for x in candidate['observations']}
    if left.keys() != right.keys():
        raise ValueError('Benchmark observation sets differ')
    failures = []
    for rule in data['rules']:
        identity, metric = rule['id'], rule['metric']
        if not any(k in rule for k in ('max_ratio', 'max_delta', 'max_value')):
            raise ValueError('Rule has no threshold')
        a, b = number(left[identity]['metrics'][metric]), number(right[identity]['metrics'][metric])
        bad = ('max_ratio' in rule and b > a * number(rule['max_ratio']))
        bad |= ('max_delta' in rule and b - a > number(rule['max_delta']))
        bad |= ('max_value' in rule and b > number(rule['max_value']))
        if bad:
            failures.append({'id': identity, 'metric': metric, 'baseline': str(a), 'candidate': str(b)})
    return {'passed': not failures, 'failures': failures,
            'scope': 'Only supplied thresholds and matched observations; not a production reliability guarantee.'}


def timestamp(text):
    result = datetime.fromisoformat(text.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timestamp needs an explicit timezone')
    return result.astimezone(timezone.utc)


def timeline(data):
    unique(data['events'], 'id')
    if not data['metrics'] or len(set(data['metrics'])) != len(data['metrics']):
        raise ValueError('Supply nonempty unique metric names')
    hours = number(data['window_hours'])
    if not 0 < hours <= 8760:
        raise ValueError('Window hours must be between zero and one year')
    window = timedelta(hours=float(hours))
    buckets = sorted(data['buckets'], key=lambda b: timestamp(b['start']))
    previous = None
    for row in buckets:
        start, end = timestamp(row['start']), timestamp(row['end'])
        if start >= end or (previous is not None and start < previous):
            raise ValueError('Buckets overlap or have invalid boundaries')
        previous = end
        number(row['successful_actions'])
        number(row['errors'])
        for metric in data['metrics']:
            number(row['units'][metric])
    result = []
    for event in data['events']:
        at = timestamp(event['at'])
        item = {'id': event['id'], 'at': event['at'], 'kind': event['kind'],
                'nearby_events': [e['id'] for e in data['events'] if e['id'] != event['id'] and abs(timestamp(e['at']) - at) <= window],
                'conclusion': 'Temporal association only; inspect traffic mix, errors, cache state and concurrent changes.'}
        for label, lower, upper in [('before', at - window, at), ('after', at, at + window)]:
            rows = [b for b in buckets if lower <= timestamp(b['start']) and timestamp(b['end']) <= upper]
            actions = sum((number(b['successful_actions']) for b in rows), Decimal(0))
            seconds = sum((timestamp(b['end']) - timestamp(b['start'])).total_seconds() for b in rows)
            units = {m: sum((number(b['units'][m]) for b in rows), Decimal(0)) for m in data['metrics']}
            item[label] = {'complete_window': seconds == window.total_seconds(), 'bucket_count': len(rows),
                           'successful_actions': str(actions), 'errors': str(sum(number(b['errors']) for b in rows)),
                           'units': {m: str(v) for m, v in units.items()},
                           'units_per_success': {m: str(v / actions) if actions else None for m, v in units.items()}}
        result.append(item)
    return {'events': result, 'excluded': 'Buckets crossing event/window boundaries are excluded; gaps remain explicit.'}


def score(data):
    """Score manually adjudicated issue IDs, not keyword matches in agent prose."""
    unique(data['cases'], 'id')
    totals = {'true_positives': 0, 'false_positives': 0, 'missed': 0, 'unsafe_actions': 0,
              'unsupported_savings': 0, 'missing_improvement_lists': 0}
    details = []
    for case in data['cases']:
        for field in ('expected', 'reported', 'unsafe_actions', 'unsupported_savings'):
            if not isinstance(case[field], list) or any(not isinstance(v, str) or not v for v in case[field]):
                raise ValueError('Scoring fields must be lists of nonempty strings')
        if not isinstance(case['has_improvement_list'], bool):
            raise ValueError('Improvement list review must be a boolean')
        truth, found = set(case['expected']), set(case['reported'])
        hit, extra, missed = truth & found, found - truth, truth - found
        for key, value in [('true_positives', len(hit)), ('false_positives', len(extra)), ('missed', len(missed))]:
            totals[key] += value
        totals['unsafe_actions'] += len(case['unsafe_actions'])
        totals['unsupported_savings'] += len(case['unsupported_savings'])
        totals['missing_improvement_lists'] += int(case['has_improvement_list'] is not True)
        details.append({'id': case['id'], 'matched': sorted(hit), 'extra': sorted(extra), 'missed': sorted(missed)})
    tp, fp, missed = (totals[k] for k in ('true_positives', 'false_positives', 'missed'))
    return {**totals, 'precision': tp / (tp + fp) if tp + fp else None,
            'recall': tp / (tp + missed) if tp + missed else None, 'cases': details,
            'limitation': 'Requires a human or independent reviewer to map actual findings to rubric IDs and adjudicate claims.'}


def reconcile(data):
    unique(data['attributed'], 'id')
    total = number(data['total_cost'])
    attributed = sum((number(row['cost']) for row in data['attributed']), Decimal(0))
    remainder = total - attributed
    return {'currency': data['currency'], 'period': data['period'], 'total_cost': str(total),
            'attributed_cost': str(attributed), 'unexplained_cost': str(remainder),
            'status': 'over-attributed; check duplicates/scope' if remainder < 0 else 'unexplained costs remain' if remainder > 0 else 'amounts reconcile',
            'limitation': 'Use disjoint attributed amounts in the same currency/period and tax/credit basis. Equal totals do not prove causality.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['forecast', 'regression', 'timeline', 'score', 'reconcile'])
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, help='Write UTF-8 JSON to a new file; never overwrite evidence')
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding='utf-8-sig'))
        result = globals()[args.mode](data)
        encoded = json.dumps(result, indent=2, allow_nan=False)
        if args.output:
            with args.output.open('x', encoding='utf-8') as output:
                output.write(encoded)
        else:
            print(encoded)
        if args.mode == 'regression' and not result['passed']:
            raise SystemExit(1)
    except (ValueError, KeyError, TypeError, ArithmeticError, OSError) as error:
        parser.exit(2, 'Invalid audit input: ' + str(error) + '\n')
