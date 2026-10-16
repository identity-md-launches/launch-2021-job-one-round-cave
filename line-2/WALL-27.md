# The First Sieve — Pepe 27

ZipGate adds a central-directory resource gate before SafeZip's ZIP parser runs.
It catches inflated or false directory counts and byte sizes, then binds the
second SafeZip snapshot to the checked bytes by SHA-256. Existing tools and the
line's goal remain unchanged. Run the working public-data demonstration:

```sh
python3 -B line-2/tools/zipgate/demo.py
```

The demo refused a 60,000-byte directory comment against a 1,024-byte budget,
then extracted all 23,132 bytes of the bundled real public IMD API capture with
one entry, 67 directory bytes and three nodes. It made no network request.
28 new adversarial tests and 76 inherited tests passed. Tests verify refusals
before ZIP parsing, including a ZIP64 locator hidden inside a member comment.
This gates parser inputs; it is not a hard RAM, CPU or hostile-local-race sandbox.
See the tool README for format restrictions and remaining boundaries.

The added mark is a shallow woven sieve holding three dark stones while small
ochre grains fall through. It sits on previously bare upper-left rock. The
built-in image tool generated its pigment; the inherited local PNG/JPEG codec
assembled only that pigment onto the old wall. One source generation was used.
The first composite was too pale, so the same pigment was assembled with darker
earth tones. No draft, crop or standalone pigment picture remains in the tree.

- `artifacts/line-2/wall-v8.png`: 1254 × 1254, opaque RGB PNG, 2,822,814 bytes.
- `artifacts/line-2/wall.png`: identical continuation wall.
- `dist/line-2/27.jpg`: 512 × 512 JPEG, 89,033 bytes.
- `dist/line-2/27.json`: record 27, count-plus-one from 26 inherited records.

Visual inspection of the complete PNG and JPEG found no new words, numbers,
logos, frames or hands. Pepe's wide mouth, heavy lids and both five-digit hands
remain untouched. The decoded-pixel comparison found 9,605 changed pixels within
x=255..414, y=230..389 and zero outside. All 1,562,911 remaining pixels are
identical. PNG round-trip and installed image-structure checks passed.

No unmet requirement was observed in the added mark. The inherited rock retains
its photographic appearance as required by preservation; fine weave detail is
less distinct in the 512-pixel preview. This is the worker's review, not an
independent visual certification. The explicit record-adjacent JPEG requirement
is followed despite the brief's general pictures-only-in-artifacts sentence.
No other preview picture was saved. `media-check-27.json` records hashes and
counts; `review-27.json` records formats, tests and limitations.
