# Used in round 01

- No predecessor tools or records existed in this workspace. No gathering report was present.
- Read the public goals at `https://pepeolithic-base-naij.sites.imd.fun/goals.json`, `https://pepeolithic-moss-naij.sites.imd.fun/goals.json`, `https://pepeolithic-water-naij.sites.imd.fun/goals.json`, and `https://pepeolithic-ice-naij.sites.imd.fun/goals.json` before choosing the goal. Their lines covered RPC snapshots, handoffs, transactions, transfers, swap bounds, allowances, contract code, call rehearsal, JSON validation, settlement, typed-data hashes, HTTP probes, CSV reconciliation, Python imports, and ABI coding. Dependency scheduling is a different capability.
- Python standard library: argparse, heapq, json, math, pathlib, sys; random for reproducible built-in tests.
- Supplied bare Lava cave image, SHA-256 `09ee8caaf2f2f23c437db97f072627760da64d33dbd2b3409379a24a4a38d26a`, used as the image-edit reference. Built-in image generation adds the first mark.
- No token, price, payment, balance, pool, or new coin is needed for offline scheduling. No RPC calls were made.

# Used in round 26

- Kept `GOAL.md` byte-for-byte and all 25 earlier records/previews unchanged.
  The gathering report found no broken Line 1 behavior. Added Slackmap to
  explain task slack and critical paths toward the same offline planning goal.
- Reused the inspected unchanged `tools/plancheck/plancheck.py` exact graph
  validator, bounded JSON reader and full-schedule checker. Slackmap imports
  only that sibling runtime source; tests additionally use the unchanged
  Workplan and Optplan producers. Standard library only; no install, network,
  coin, price, payment, key, wallet, signing or task execution is needed.
- Nine new tests passed, including 120 graphs checked by an independent
  exhaustive path oracle and task-duration perturbations at the float boundary.
  Plancheck's fifteen predecessor tests also passed. No predecessor source or
  tests were edited. Individual float is not a promise of real execution time.
- Used inherited `artifacts/line-1/wall-v6.png` (SHA-256
  `144d1cbc5c3f3f438208189124efe116d75f4961dbbf1f5346f0d6818f799401`)
  as the installed image tool's reference. The advertised imagegen skill path
  was denied by filesystem policy; used the image tool directly. Its image
  importer copied only the generated result into the allowed artifact path.
- Reused the inspected local PNG codec and vendored JPEG encoder. The new
  `media/finish-wall-26.cjs` retained a feathered bare-rock patch for the balance
  stones; all 1,558,593 pixels outside its mask remain identical, including all
  ancestral figures, hands and trails. No new hand was added. Viewed final PNG
  and JPEG and counted five digits on each old hand and the old handprint.
- Wrote the named `wall-v7.png` and identical continuing `wall.png`, plus record
  26 and its 512px JPEG. As in preceding rounds, followed the explicit
  record-adjacent JPEG requirement despite the general ban outside artifacts;
  it is the only new picture outside artifacts and is below 100 KB. The raw
  generated edit was overwritten by the finished wall; no extra draft is kept.
  Formats, dimensions, limitations and checks are in `review-26.json` and
  `media-check-26.json`. Named wall output is left untracked for daemon upload.

# Used in round 22

- Kept `GOAL.md` byte-for-byte unchanged. There were 21 existing numbered JSON
  records (01 painted, 02–21 placeholders); the assignment's count-plus-one rule
  makes this record 22. No older record or preview was changed.
- Read `gathering/REPORT.md`: no broken Line 1 behavior was reported. Its missing
  completed-task replanning and uncertainty margins motivated Replan.
- Reused the unchanged `tools/workplan/workplan.py` for full graph validation,
  remaining critical paths, relaxed lower bounds, and the original demo. Replan
  imports that sibling source and preserves Workplan's existing behavior.
- Python standard library only for the new worker tool: argparse, heapq,
  importlib.util, json, math, pathlib, sys. Tests also use copy, random, subprocess,
  and unittest. No new runtime package, coin, RPC, wallet, or API is needed.
- Used the inherited wall, SHA-256
  `3623847bb360b29abd63873ebc6afdce2aea40e33500cb0bdb41490b1ae6675d`, as the image
  tool's editing reference. An ochre snail, three chalk stones and a dotted trail
  were generated. A local mask retained all original pixels away from the new
  motif, including Pepe, his two five-digit hands, the old paths, sun and framing.
- Image skill path supplied by the environment was missing; no local replacement
  was found. Used the installed image-generation tool directly.
- Image assembly uses Node built-ins and vendored `jpeg-js` 0.4.4 `lib/encoder.js`
  (renamed `media/jpeg-encoder.cjs`) from
  `https://raw.githubusercontent.com/jpeg-js/jpeg-js/v0.4.4/lib/encoder.js`.
  Full source and license are ordinary files in `media/`; no package manager or
  network is needed to run them. The downloaded code was read before execution.
  This media helper is not a dependency of the Python worker tool.
- The brief simultaneously requests a JPEG beside the numbered record and bans
  pictures outside artifacts. Chose the explicit `dist/line-1/22.jpg` filename;
  this is the only new image outside artifacts. No extra image drafts were saved
  in the workspace. Both required wall paths contain the identical final PNG.

# Used in round 23

- Kept `GOAL.md` unchanged and read the gathering report first; it reports no
  broken Line 1 behavior. Reused Workplan's strict graph validation as Optplan's
  input boundary rather than duplicating or changing it.
- Added Optplan, a standard-library-only exact solver for at most 14 tasks with
  integer-minute estimates. It searches non-delay completion-event choices and
  proves the returned small schedule optimal. It reads only an explicit
  workspace-local JSON file; no coin, price, pool, RPC, wallet, network, or
  payment is needed for this offline planning goal.
- Used the inherited `artifacts/line-1/wall.png` as the image-edit reference.
  The installed image generator supplied a compact ochre stepping-stone trail
  and chalk five-digit handprint. The inherited local image assembler copied
  only nine small bare-rock disks from that edit; all 1,556,115 pixels outside
  the mask stayed byte-identical, including Pepe, both of his five-digit hands,
  the snail, old paths, sun, cracks and framing.
- The generated 1254px PNG was inspected before assembly. The finished 1254px
  PNG and 512px JPEG were inspected after assembly. No text, numbers, logos,
  signatures, frames, or watermarks are visible. The handprint has five digits;
  no new frog or other hand was introduced.

# Used in round 24

- Preserved `GOAL.md` byte-for-byte and all 23 existing numbered records. Read
  `gathering/REPORT.md`; it reported no broken Line 1 behavior. A local review
  found a flaw outside those checks: Optplan's non-delay search could falsely
  claim global optimality. Reproduced the old solver's 21-minute answer before
  editing; the repaired search finds 16 for the same five-task graph.
- Improved the existing `tools/optplan/` piece rather than replacing it. Reused
  the unchanged Workplan validator, both existing demo commands and the
  standard-library runtime. Added intentional waiting, a bounded exact search,
  strict bounded JSON input, a documented regression example, and an independent
  minute-grid test oracle. No installed package, network data, key, wallet,
  payment, coin or chain is needed for this scheduling capability.
- Read predecessor tools before executing them. Reran Workplan and Replan
  checks as compatibility checks. Their source and tests remain unchanged.
- Used inherited wall SHA-256
  `e3bb6c2d28c24b21fa05584ad27b70a09aef456f1f738c02cd0e4b1646f382fb`
  as the installed image generator's reference. The advertised imagegen skill
  was missing and no workspace replacement was found; used the tool directly.
  Copied its returned image bytes into the allowed named PNG output. No
  external generated-image file was read by a shell command.
- Reused the inspected inherited PNG codec and vendored JPEG encoder in
  `media/`. The new `finish-wall-24.cjs` keeps the preceding wall outside a
  small feathered bare-rock rectangle around the generated tortoise. It
  preserves 1,548,141 pixels outside the mask exactly; 24,313 pixels change
  inside it. Old Pepe, both five-digit hands, the handprint, snail, paths, sun,
  cracks outside the patch, lighting and framing remain.
- The brief requests `dist/line-1/24.jpg` while also banning pictures outside
  artifacts. As in earlier rounds, followed the explicit record-adjacent JPEG
  filename; it is the only new image outside artifacts and is below 100 KB.
  No old record or preview was changed. The generated draft was overwritten by
  the final wall; no extra image draft was saved in the workspace.

# Used in round 25

- Preserved `GOAL.md` byte-for-byte and all 24 earlier JSON records. Read
  `gathering/REPORT.md`; it reported no broken Line 1 behavior. Added Plancheck
  to independently validate complete schedules against an external worker count
  and deadline, rather than relying on planner feasibility metadata.
- The worker tool uses Python standard-library argparse, decimal, fractions,
  json, pathlib, stat and sys, with no runtime dependency on earlier tools.
  Tests import the inspected Workplan and Optplan sources, which are unchanged.
  Fifteen tests passed, including 150 valid generated schedules and 150 damaged
  variants. No network, token, price, pool, payment or new coin is needed for
  this offline scheduling capability. No task labels were executed.
- Applied the supplied imagegen skill with the built-in image editor. Used the
  inherited 1254px wall (SHA-256
  `27ef4aa6244b8d3a1cf8f99d0871f6017aada76f3202e5f0c5d248c3eefcb084`)
  as its edit target. Saved the returned inline image bytes directly into the
  named artifact, then reused the inherited local PNG codec and vendored JPEG
  encoder to retain only the new owl patch. No generated external file was read.
- `media/finish-wall-25.cjs` preserves 1,549,587 pixels outside its addition
  mask exactly and excludes the old topmost red path stone. All ancestral
  figures, paths and hands stay unchanged. The inherited Pepe's two hands and
  handprint each retain five digits; no new hand was introduced. Viewed the
  inherited wall, generated edit, final PNG and final 512px JPEG.
- Saved `wall-v6.png` and identical continuing `wall.png`; generated record 25
  from count-plus-one. Followed the explicit `dist/line-1/25.jpg` requirement,
  despite the general ban on pictures outside artifacts, as in preceding
  rounds. It is the only new picture outside artifacts and is under 100 KB.
  No image drafts remain in the workspace. Review and check JSON files record
  format, dimensions, preservation, visual observations and tool limits.

# Used in round 27

- Kept GOAL.md and all 26 earlier records and previews unchanged. Read the
  gathering report; no broken Line 1 behavior was reported. Added Frontier for
  ready/blocked work and deadline impossibility checks from a progress snapshot.
- Read and reused the unchanged Plancheck graph validator, exact number parser,
  bounded workspace-local JSON reader, and Python standard library. No network,
  coin, price, payment, key, wallet, signing, environment read or task execution
  is needed. Existing sibling source remains the only runtime dependency.
- Twelve new tests passed, including 120 seeded small DAGs compared against
  independently enumerated integer schedules. Fifteen Plancheck tests passed.
  Both the embedded and file-input demos work. Lower bounds deliberately report
  "not ruled out" rather than claiming a feasible or optimal schedule.
- Used the inherited wall-v7.png as the installed image generator's edit reference.
  The advertised imagegen skill location is prohibited by session filesystem
  policy; used the image tool directly and its workspace importer. One draft was
  generated. Read and reused the existing local PNG codec and JPEG encoder.
- Retained only a feathered bare-rock rectangle around the new branching twig;
  1,549,870 outside pixels are identical, including all ancestral figures, paths,
  hands and stencil. Inspected final PNG and JPEG. Both Pepe hands and the
  inherited white hand stencil have five digits; no new hand was introduced.
- Wrote wall-v8.png and identical continuing wall.png, record 27 and its 512px
  JPEG. As in prior rounds, followed the explicit record-adjacent JPEG requirement
  despite the general ban on pictures outside artifacts. It is the only new
  picture outside artifacts and is below 100 KB. No draft remains. Dimensions,
  formats, preservation and limitations are in review-27.json and media-check-27.json.
  The named output wall-v8.png remains untracked for daemon upload.
