# ledger

Builds the monthly per-account report that finance reconciles against.
Every night the legacy ERP drops fresh export files and the nightly job runs
`./ci.sh`; the report is only published when CI is green.

## Running

    ./ci.sh                       # the full pipeline (what the nightly job runs)
    python -m ledger.cli build --config config/settings.json --out dist/report.json

Paths in `inputs` (in the settings file) are relative to the settings file.

## Export format

- One CSV file per office, exported by the legacy ERP in **Windows-1252**.
- Columns: `id, timestamp, account, currency, amount, description`.
- Fields may carry padding whitespace; it is not significant.
- `timestamp` is ISO-8601 with the UTC offset of the office that booked the
  transaction, e.g. `2024-03-31T23:30:00-05:00`.
- `amount` is in accounting notation: thousands separators (`1,234.50`), and
  negatives (refunds) are written either `-45.00` or in parentheses `(45.00)`.
- `id` is unique **within one export file**. The same id may appear again in a
  different file; those are different transactions. If an id repeats inside a
  single file, the later rows are ERP re-sends: only the first row counts and
  the others are counted as duplicates.

## Reporting rules

- Amounts are converted to the base currency with the rates in the settings file.
- Each transaction is converted and then rounded to whole cents, ties away from
  zero (`ROUND_HALF_UP`: 8408.5 -> 8409 and -8408.5 -> -8409). The report sums
  those per-transaction cent values.
- A transaction belongs to the calendar month in which it happened **as written
  in the export** (the booking office's local date), not the UTC date.
- `largest` is, per account, the transaction with the greatest *absolute*
  converted amount (the first one wins a tie).
- Descriptions are reported with surrounding whitespace trimmed.

## Report format

    {
      "base_currency": "USD",
      "transactions": 123,            # counted after dropping duplicates
      "duplicates_dropped": 4,
      "accounts": {
        "<account>": {
          "months": {"2024-01": 12345, ...},   # cents, sorted by month
          "total_cents": 12345,
          "largest": {"id": "T0001", "amount_cents": -5000, "description": "..."}
        }
      }
    }
