# Testomat → Flaky CSV (offline)

Offline tool that turns **Testomat run JSON** into a CSV with `trend_last5`, flaky detection and reasons — **no API, no credits**.  
Repo: https://github.com/dashatsion/testomat-flaky-csv

## What it does
- Builds `_flaky_overview.csv` with columns:
  `run_at,run_id,title,status,retries,duration_ms,trend_last5,is_flaky,reasons`
- Flaky rules:
  - **R1**: ≥2 fails in last 5 runs → flaky
  - **R3**: Passed with >1 retry → +20
  - **R4**: Duration instability: `max/median ≥ 5` or `stdev/mean ≥ 0.6` → +20
  - Mark `is_flaky=yes` if score ≥ 40 or R1 triggered.

## Requirements
- Python 3 (macOS/Linux/WSL). No external deps.

## Install
```bash
git clone git@github.com:dashatsion/testomat-flaky-csv.git
cd testomat-flaky-csv
```

## Get JSON from Testomat
1. Open a **Run** page → DevTools → **Network** → enable **Preserve log**.
2. Filter **Fetch/XHR** or search `testruns`.
3. Open `testruns?...page=1&run_id=...` → **Copy → Copy response**.
4. Save to file (macOS example):
```bash
mkdir -p ~/path/to/testomat_runs
pbpaste > ~/path/to/testomat_runs/run_2025-09-16.json
python3 -m json.tool ~/path/to/testomat_runs/run_2025-09-16.json >/dev/null && echo "JSON OK"
```

### Pagination
If the response contains `meta.total_pages > 1`, save all pages as `..._p1.json`, `..._p2.json`, … and either:
- run the converter for each file; or
- merge pages into one JSON via `scripts/merge_pages.py` (see below).

## Run the converter
```bash
mkdir -p ~/path/to/flaky_tests
python3 scripts/flaky_from_testomat.py   ~/path/to/testomat_runs/run_2025-09-16.json   ~/path/to/flaky_tests/_flaky_overview.csv
open -R ~/path/to/flaky_tests/_flaky_overview.csv  # macOS: reveal file
```

### Batch convert many JSON files
```bash
for f in ~/path/to/testomat_runs/run_*.json; do
  python3 scripts/flaky_from_testomat.py "$f" ~/path/to/flaky_tests/_flaky_overview.csv
done
```

## Merge paginated pages into one JSON (optional)
```bash
python3 scripts/merge_pages.py   --glob '~/path/to/testomat_runs/run_c4883898_p*.json'   --out  '~/path/to/testomat_runs/run_c4883898_all.json'

python3 scripts/flaky_from_testomat.py   ~/path/to/testomat_runs/run_c4883898_all.json   ~/path/to/flaky_tests/_flaky_overview.csv
```

## Notes
- Do **not** commit real run data (JSON/CSV) — `.gitignore` excludes them by default.
- Examples in `examples/` should be synthetic only.

## License
MIT © 2025 Dashas Tion
