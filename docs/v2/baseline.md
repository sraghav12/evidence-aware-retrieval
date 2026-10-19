# V2 baseline

Source revision: `675733109b30e80ce40c0a796bc0dd89e616c4ef`. Original working changes were not copied. New branch: `feat/evidence-aware-v2`.

Clean baseline: 23 tests passed in 4.72 seconds on Python 3.12.9. All 24 tracked v1 release files (8 under `data/release/v1`, 16 under `results/release_v1`) have SHA-256 entries in `v1_files_sha256.json`. An earlier note said 26: `results/release_v1/review_records.json` and `run.log` are gitignored local files in the source checkout, absent from the clone and not covered, so the design's `results/release_v1` aggregate (`780f29…`) cannot be reproduced here. The `data/release/v1` aggregate matches.

Local Git clone hit an Apple Git initial-ref-transaction assertion after object transfer. The objects and origin/main ref were intact; explicit branch checkout from origin/main recovered the new checkout without touching the source.
