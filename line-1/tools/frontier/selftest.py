import copy
from fractions import Fraction
import itertools
import random
import unittest
import frontier as f


class FrontierTests(unittest.TestCase):
    def setUp(self):
        self.data = {'tasks': [{'id': 'a', 'minutes': 2}, {'id': 'b', 'minutes': 3, 'after': ['a']}, {'id': 'c', 'minutes': 1}]}
        self.progress = {'completed': [], 'running': []}

    def run_model(self, **kw):
        return f.analyze(kw.get('data', self.data), kw.get('progress', self.progress), kw.get('workers', 2), kw.get('elapsed', 0), kw.get('budget', 10))

    def test_demo(self):
        r = f.demo()
        self.assertEqual(r['ready'][0]['task'], 'fixtures')
        self.assertEqual(r['remaining_lower_bound'], '6')
        self.assertEqual(r['free_workers'], 1)

    def test_frontier(self):
        r = self.run_model()
        self.assertEqual([x['task'] for x in r['ready']], ['a', 'c'])
        self.assertEqual(r['blocked'], [{'task': 'b', 'waiting_for': ['a']}])

    def test_active_overrun(self):
        r = self.run_model(progress={'completed': [], 'running': [{'task': 'a', 'remaining': 10}]}, elapsed=3, budget=15)
        self.assertEqual(r['remaining_lower_bound'], '13')
        self.assertEqual(r['deadline_status'], 'impossible_at_estimates')

    def test_completed_closure(self):
        for p in ({'completed': ['b'], 'running': []}, {'completed': [], 'running': [{'task': 'b', 'remaining': 1}]}):
            with self.assertRaises(ValueError): self.run_model(progress=p)

    def test_bad_progress(self):
        for p in ({'completed': ['z'], 'running': []}, {'completed': ['a', 'a'], 'running': []},
                  {'completed': ['a'], 'running': [{'task': 'a', 'remaining': 1}]},
                  {'completed': [], 'running': [{'task': 'a', 'remaining': 0}]},
                  {'completed': [], 'running': [{'task': 'a', 'remaining': 1}, {'task': 'a', 'remaining': 1}]},
                  {'completed': [], 'running': [], 'extra': True}):
            with self.assertRaises(ValueError): self.run_model(progress=p)

    def test_bad_numbers(self):
        for w in (0, True, 65, 1.5):
            with self.assertRaises(ValueError): self.run_model(workers=w)
        for e in (-1, float('inf'), True):
            with self.assertRaises(ValueError): self.run_model(elapsed=e)

    def test_zero_capacity(self):
        p = {'completed': [], 'running': [{'task': 'a', 'remaining': 1}, {'task': 'c', 'remaining': 1}]}
        self.assertEqual(self.run_model(progress=p)['free_workers'], 0)
        with self.assertRaises(ValueError): self.run_model(progress=p, workers=1)

    def test_complete_and_late(self):
        p = {'completed': ['a', 'b', 'c'], 'running': []}
        r = self.run_model(progress=p)
        self.assertEqual(r['deadline_status'], 'complete')
        self.assertEqual(r['remaining_lower_bound'], '0')
        self.assertEqual(self.run_model(progress=p, elapsed=11)['deadline_status'], 'impossible_at_estimates')

    def test_exact_decimal(self):
        data = {'tasks': [{'id': n, 'minutes': 0.1} for n in 'abc']}
        r = self.run_model(data=data, workers=2, budget=0.15)
        self.assertEqual(r['capacity_lower_bound'], '3/20')
        # Necessary bounds pass even though three indivisible jobs need 0.2.
        self.assertEqual(r['deadline_status'], 'not_ruled_out')

    def test_cycle_and_duplicates(self):
        for data in ({'tasks': [{'id': 'a', 'minutes': 1, 'after': ['a']}]}, {'tasks': self.data['tasks'] * 2}):
            with self.assertRaises(ValueError): self.run_model(data=data)

    def test_no_mutation(self):
        old = copy.deepcopy((self.data, self.progress))
        self.run_model()
        self.assertEqual(old, (self.data, self.progress))

    def test_seeded_bounds_against_independent_grid_oracle(self):
        rng = random.Random(27)
        for _ in range(120):
            n = rng.randint(1, 5)
            names = list('abcde'[:n])
            durations = {a: rng.randint(1, 3) for a in names}
            deps = {a: {b for b in names[:i] if rng.random() < .3} for i, a in enumerate(names)}
            workers = rng.randint(1, 3)
            # Exhaust all ready subsets at each integer tick, including idling.
            states = {(frozenset(), ())}
            optimum = None
            for minute in range(sum(durations.values()) + 1):
                if any(len(done) == n for done, active in states):
                    optimum = minute
                    break
                following = set()
                for done, active in states:
                    busy = dict(active)
                    ready = [a for a in names if a not in done and a not in busy and deps[a] <= done]
                    for size in range(min(workers - len(busy), len(ready)) + 1):
                        for selected in itertools.combinations(ready, size):
                            running = dict(busy, **{a: durations[a] for a in selected})
                            finished = done | {a for a, left in running.items() if left == 1}
                            next_active = tuple(sorted((a, left - 1) for a, left in running.items() if left > 1))
                            following.add((frozenset(finished), next_active))
                states = following
            data = {'tasks': [{'id': a, 'minutes': durations[a], 'after': sorted(deps[a])} for a in names]}
            r = self.run_model(data=data, workers=workers, budget=optimum)
            self.assertLessEqual(Fraction(r['remaining_lower_bound']), optimum)
            self.assertEqual({x['task'] for x in r['ready']}, {a for a in names if not deps[a]})
            self.assertEqual(r['deadline_status'], 'not_ruled_out')


if __name__ == '__main__': unittest.main()
