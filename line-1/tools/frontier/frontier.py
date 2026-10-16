#!/usr/bin/env python3
"""Read an offline progress snapshot; report ready work without executing it."""
import argparse
from decimal import Decimal
from fractions import Fraction
import heapq
import importlib.util
import json
from pathlib import Path
import sys

_spec = importlib.util.spec_from_file_location('frontier_plancheck', Path(__file__).resolve().parents[1] / 'plancheck/plancheck.py')
pc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pc)


def exact(value):
    # Fraction strings retain exactness even when work / workers repeats.
    return str(value.numerator) if value.denominator == 1 else str(value)


def analyze(data, progress, workers, elapsed, budget):
    tasks = pc.graph(data)
    if type(workers) is not int or not 1 <= workers <= 64:
        raise ValueError('workers must be an integer from 1 to 64')
    now, deadline = pc.number(elapsed, 'elapsed'), pc.number(budget, 'budget')
    if now < 0 or deadline < 0:
        raise ValueError('elapsed and budget must be nonnegative')
    pc.keys(progress, ('completed', 'running'))
    done, active = progress['completed'], progress['running']
    if not isinstance(done, list) or any(not isinstance(n, str) for n in done) or len(set(done)) != len(done):
        raise ValueError('completed must be distinct task ids')
    done = set(done)
    if not done <= tasks.keys():
        raise ValueError('unknown completed task')
    if not isinstance(active, list) or len(active) > workers:
        raise ValueError('running must be an array no longer than workers')
    running = {}
    for row in active:
        pc.keys(row, ('task', 'remaining'))
        name = row['task']
        if not isinstance(name, str) or name not in tasks or name in done or name in running:
            raise ValueError('unknown, duplicate or completed running task')
        remaining = pc.number(row['remaining'], 'remaining')
        if remaining <= 0:
            raise ValueError('running remaining must be positive; finish zero tasks first')
        running[name] = remaining
    for name in done | running.keys():
        if not set(tasks[name][1]) <= done:
            raise ValueError('completed/running task has unfinished prerequisite: ' + name)
    remaining = {n: running.get(n, row[0]) for n, row in tasks.items() if n not in done}
    deps = {n: set(tasks[n][1]) - done for n in remaining}
    children = {n: [] for n in remaining}
    degree = {n: len(ds) for n, ds in deps.items()}
    for n, ds in deps.items():
        for d in ds:
            children[d].append(n)
    queue = [n for n in remaining if degree[n] == 0]
    heapq.heapify(queue)
    order, finishes = [], {}
    while queue:
        name = heapq.heappop(queue)
        order.append(name)
        finishes[name] = remaining[name] + max((finishes[d] for d in deps[name]), default=Fraction(0))
        for child in children[name]:
            degree[child] -= 1
            if not degree[child]:
                heapq.heappush(queue, child)
    tails = {}
    for name in reversed(order):
        tails[name] = remaining[name] + max((tails[c] for c in children[name]), default=Fraction(0))
    chain = max(finishes.values(), default=Fraction(0))
    work = sum(remaining.values(), Fraction(0))
    lower = max(chain, work / workers)
    available = deadline - now
    ready = sorted((n for n in remaining if not deps[n] and n not in running), key=lambda n: (-tails[n], n))
    return {'units': 'minutes', 'elapsed': exact(now), 'deadline': exact(deadline),
            'completed': sorted(done), 'running': [{'task': n, 'remaining': exact(running[n])} for n in sorted(running)],
            'free_workers': workers - len(running),
            'ready': [{'task': n, 'minutes': exact(remaining[n]), 'downstream_minutes': exact(tails[n])} for n in ready],
            'blocked': [{'task': n, 'waiting_for': sorted(deps[n])} for n in sorted(remaining) if deps[n]],
            'remaining_work': exact(work), 'dependency_lower_bound': exact(chain),
            'capacity_lower_bound': exact(work / workers), 'remaining_lower_bound': exact(lower),
            'available_minutes': exact(available),
            'deadline_status': 'impossible_at_estimates' if lower > available else ('complete' if not remaining else 'not_ruled_out'),
            'scope': 'Snapshot only. Lower bounds cannot prove feasibility. Ready ordering is a heuristic, not an optimal launch decision. No tasks executed.',
            'assumptions': 'Interchangeable workers; running work stays active; unfinished estimates replace original durations; no historical timing certified.'}


def demo():
    tasks = {'tasks': [{'id': 'read', 'minutes': 2}, {'id': 'build', 'minutes': 5, 'after': ['read']},
                       {'id': 'fixtures', 'minutes': 3, 'after': ['read']},
                       {'id': 'check', 'minutes': 2, 'after': ['build', 'fixtures']}]}
    progress = {'completed': ['read'], 'running': [{'task': 'build', 'remaining': 4}]}
    return analyze(tasks, progress, 2, 3, 10)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--tasks')
    parser.add_argument('--progress')
    parser.add_argument('--workers', type=int)
    parser.add_argument('--elapsed', type=Decimal)
    parser.add_argument('--budget', type=Decimal)
    args = parser.parse_args()
    try:
        values = (args.tasks, args.progress, args.workers, args.elapsed, args.budget)
        if args.demo:
            if any(v is not None for v in values):
                raise ValueError('--demo cannot combine with other options')
            result = demo()
        else:
            if any(v is None for v in values):
                raise ValueError('require --tasks --progress --workers --elapsed --budget')
            result = analyze(pc.read_json(args.tasks), pc.read_json(args.progress), args.workers, args.elapsed, args.budget)
        print(json.dumps(result, indent=2, allow_nan=False))
        return 2 if result['deadline_status'] == 'impossible_at_estimates' else 0
    except (ValueError, OSError, RecursionError, OverflowError) as exc:
        print('frontier: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
