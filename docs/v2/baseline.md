# V2 baseline

Source revision: `675733109b30e80ce40c0a796bc0dd89e616c4ef`. Original working changes were not copied. New branch: `feat/evidence-aware-v2`.

Clean baseline: 23 tests passed in 4.72 seconds on Python 3.12.9. All 26 release-file SHA-256 entries are recorded in `v1_files_sha256.json`.

Local Git clone hit an Apple Git initial-ref-transaction assertion after object transfer. The objects and origin/main ref were intact; explicit branch checkout from origin/main recovered the new checkout without touching the source.
