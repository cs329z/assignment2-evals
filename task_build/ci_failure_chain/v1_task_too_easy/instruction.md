# Get the nightly CI for `ledger` green

`/app` contains `ledger`, a small Python tool that builds a monthly per-account
report from our legacy ERP's CSV exports. The nightly job runs `/app/ci.sh`,
which is currently failing, so the report job is blocked.

Make `./ci.sh` pass by fixing the underlying problems in the source code under
`/app/ledger/`. Read `/app/README.md` first: it documents the export format and
the reporting rules that the code is supposed to implement.

Rules:

- Do not edit `ci.sh`, anything under `tests/` or `tools/`, or anything under
  `data/`. Those are shared with other teams and are restored before grading.
- The files in `data/` are only samples. New exports arrive every night in the
  same documented format, so the code must be correct for any export that
  follows the README, not just for the files that are here. Do not
  special-case, skip, or loosen any check.
- The visible tests do not cover every rule in the README. A green `./ci.sh` is
  required but not sufficient: your fix is also checked against other exports.
- Keep the names the tests import working (`ledger.models.Transaction`,
  `ledger.parsing.parse_amount`, `ledger.parsing.parse_rows`,
  `ledger.money.to_cents`, `ledger.aggregate.build_report`) and keep the
  `python -m ledger.cli build --config ... --out ...` command-line interface.

The task is done when `./ci.sh` exits 0 and the report is correct for every
rule in the README.
