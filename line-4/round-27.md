# Pepe 27 — The Two Entrances

[AuthCheck](tools/authcheck/README.md) extends line 4's unchanged OpenAPI
compatibility goal to authentication alternatives and scope/role requirements.
It detects when a previously sufficient option no longer satisfies any new
option, and retains earlier schema findings and unresolved reviews.

```sh
python3 -B line-4/tools/authcheck/authcheck.py demo
```

The demo hypothetically removes anonymous discovery access from the real captured
IMD description. It finds one potential break and one retained review across five
operations. All 116 tests passed, including 65,536 policy comparisons against an
independent finite model. The freshly fetched public description matched the
baseline byte for byte. No API operation or authentication attempt was made.

The new mark is a forked ochre trail to two charcoal cave entrances, one with a
chalk pebble at its threshold: alternative ways in, with a new requirement at one.
The full PNG is **1254 × 1254 RGB**, at `artifacts/line-4/wall-v8.png` and
`artifacts/line-4/wall.png`. The **512 × 512 JPEG** is `dist/line-4/27.jpg`,
hard-linked to its artifacts copy. The new numbered record is `27.json`.

The image tool generated the addition; narrow silhouette compositing changed
13,078 pixels on previously bare rock, with zero changes outside that silhouette.
All older marks, both five-digit hands, the rock and framing remain. Full PNG and
preview were visually inspected. The inherited rock has a photographic texture,
which was preserved; small pigment detail is less clear in the JPEG. No unmet
requirement was observed for the new mark. This is the worker's review, not
independent human approval.

[Media facts](media-check-27.json), [visual review](round-27-review.json),
[test results](check-results-27.json) and [delivery checks](delivery-check-27.json)
record the observations and limitations. The one-time media assembly helper
consumes a raw image-tool edit and overwrites it with the final wall; do not rerun
it against the already assembled output. It is separate from the Python tool.
