# Recover our legacy `.jrn` journal files

Finance is migrating off *Ledgerline*, an old accounting system whose vendor no
longer exists. It exported its journals as binary `.jrn` files. There is no
documentation and the exporter's source is lost. We need a standalone decoder so
the journals can be loaded into the new system.

`/app/samples/` has example files: each `NAME.jrn` comes with `NAME.json`, the
correct decoded output (taken from the old system's own report screen).

Write `/app/jrndecode.py`, run as:

    python /app/jrndecode.py FILE.jrn

It must print the decoded journal to stdout as one JSON document and exit 0. The
output has this shape (key order does not matter; match the samples exactly):

    {
      "default_currency": "USD",
      "accounts": ["ops", "payroll"],
      "records": [
        {"index": 0, "timestamp": "2024-03-01T09:15:30Z", "account": "ops",
         "amount": "-45.10", "currency": "USD", "memo": "Taxi", "status": "posted"}
      ]
    }

Requirements:

- It has to work on any valid `.jrn` file from this system, not just the samples.
  It will be run on other exports that you cannot see, and every field of every
  record must match. Treat the samples as the ground truth for what each field means.
- Files end with an integrity check. If a file is not a valid `.jrn` file (wrong
  magic number or failed integrity check), exit with status 2, print nothing to
  stdout, and optionally explain on stderr.
- Use only the Python 3.12 standard library, and do not read `/app/samples/` at
  runtime; the decoder is graded on its own in a clean directory.
