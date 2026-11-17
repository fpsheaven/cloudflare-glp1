#!/usr/bin/env python3
"""Offline scenario calculation for one linear meter; prices are explicit inputs."""
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path


def number(data, name, positive=False):
    value = data[name]
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise ValueError(name + ' must be a finite nonnegative number')
    value = Decimal(str(value))
    if not value.is_finite() or value < 0 or (positive and value == 0):
        raise ValueError(name + ' must be finite and ' + ('positive' if positive else 'nonnegative'))
    return value


def estimate(data):
    if not isinstance(data, dict):
        raise ValueError('Scenario must be an object')
    for label in ['meter', 'currency']:
        if not isinstance(data[label], str) or not data[label].strip():
            raise ValueError(label + ' must be a nonempty string')
    observed = number(data, 'observed_seconds', True)
    target = number(data, 'target_seconds', True)
    allowance = number(data, 'included_units')
    unit = number(data, 'price_unit_size', True)
    price = number(data, 'price_per_unit')
    values = {}
    for label in ['baseline', 'candidate']:
        projected = number(data, label + '_units') * target / observed
        billable = max(Decimal(0), projected - allowance)
        values[label] = {'projected_units': str(projected), 'billable_units': str(billable),
                         'overage_cost': str(billable / unit * price)}
    savings = Decimal(values['baseline']['overage_cost']) - Decimal(values['candidate']['overage_cost'])
    warnings = ['Scenario only; not a verified bill forecast.',
                'Aggregate shared-allowance usage before running. Fixed fees, taxes, tiers and rounding excluded.']
    if observed < 86400:
        warnings.append('Observation is shorter than one complete day; do not use as a reliable monthly forecast.')
    if savings < 0:
        warnings.append('Candidate increases modeled cost.')
    return {'meter': data['meter'], 'currency': data['currency'],
            'observed_seconds': str(observed), 'target_seconds': str(target),
            **values, 'modeled_savings': str(savings), 'warnings': warnings}


if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise ValueError('Usage: estimate_cost.py scenario.json')
        data = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'), parse_float=Decimal)
        print(json.dumps(estimate(data), indent=2))
    except (KeyError, ValueError, InvalidOperation, OSError) as error:
        print('Cost estimate failed: ' + str(error), file=sys.stderr)
        sys.exit(1)
