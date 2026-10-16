# Frontier

See what can start next in an offline dependency plan after some work has finished.
Frontier lists ready tasks, running work, unfinished prerequisites and free workers.
It ranks ready tasks by longest downstream work, then task ID. It computes exact
remaining dependency and worker-capacity lower bounds against an absolute deadline.
It reads data only; task IDs are never executed.

From the repository root, one command shows it working:

```sh
python3 -B line-1/tools/frontier/frontier.py --demo
```

Tried locally: the demo has `read` completed, `build` running with four minutes
left, and one free worker. It offers `fixtures`, blocks `check`, and computes a
six-minute lower bound with seven minutes available. Twelve tests passed,
including 120 seeded small DAGs compared with an independent exhaustive integer
scheduling oracle. Existing Plancheck tests also passed. These are local checks,
not an independent certification or a guarantee about actual work time.

For your own snapshot:

```sh
python3 -B line-1/tools/frontier/frontier.py --tasks line-1/tools/frontier/tasks.json --progress line-1/tools/frontier/progress.json --workers 2 --elapsed 3 --budget 10
```

`tasks.json` uses the existing Plancheck format: one `tasks` array, each item
having a unique `id`, positive `minutes`, and optional distinct `after` IDs.
`progress.json` has exactly `completed` (distinct IDs) and `running` (objects
with `task` and positive `remaining`). The bundled files reproduce the demo.
Completed and running tasks must have all prerequisites completed; a running
job occupies one worker. Remaining time may exceed the original estimate.
Use an empty running array for a checkpoint with no active work. Mark zero-time
remaining jobs completed before taking a snapshot.

`elapsed` is minutes since the original start; `budget` is the original absolute
deadline, not additional time. Both are nonnegative. Numbers use exact finite
JSON decimal values (up to 100 digits and exponent magnitude 100). Output
numbers are strings: integers or exact fractions such as `9/2`.

Exit 0 means complete or deadline **not ruled out**, 2 means impossible at the
supplied estimates, and 1 means malformed input. A passed lower bound does not
prove feasibility: three independent 0.1-minute jobs on two workers have a
0.15-minute work bound but require 0.2 minutes. Ready priority is only a
heuristic; intentional waiting can improve a schedule. Use Optplan for small
integer cases and Plancheck to validate an actual full proposed schedule.

Limits: 1–500 tasks, 1–64 interchangeable workers, input files at most 100,000
bytes each, ordinary workspace-local files only. Imports only the unchanged
sibling `../plancheck/plancheck.py` plus Python standard library. Keep that file
when copying the tool. No network, installation, environment reads, clock,
wallet, credentials or task execution. The snapshot is an assertion by the
caller: it does not verify past worker use, actual completion, calendars,
skills, preemption or real execution time. If everything is complete after the
deadline it reports impossible at estimates because the deadline has passed;
it does not infer when completion occurred.

Run tests:

```sh
python3 -B line-1/tools/frontier/selftest.py
```
