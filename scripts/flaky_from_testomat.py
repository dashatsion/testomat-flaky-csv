#!/usr/bin/env python3
"""
Convert Testomat run JSON -> update CSV with flaky detection.

Usage:
  python3 scripts/flaky_from_testomat.py /path/to/run.json /path/to/_flaky_overview.csv

CSV columns:
  run_at,run_id,title,status,retries,duration_ms,trend_last5,is_flaky,reasons

Rules:
  R1: >=2 fails in last 5 -> +40 (flaky if true)
  R3: passed with retries > 1 -> +20
  R4: duration instability: max/median >= 5.0 OR stdev/mean >= 0.6 -> +20
  Mark is_flaky="yes" if score >= 40 or R1 is true.
"""
import csv, json, sys, os, statistics
from datetime import datetime

HEADERS = ["run_at","run_id","title","status","retries","duration_ms","trend_last5","is_flaky","reasons"]
DURATION_SPIKE_FACTOR = 5.0

def load_json(path):
    with open(path, "rb") as f:
        data = f.read()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        sys.exit(f"[ERROR] File is not UTF-8 JSON: {path}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        sys.exit(f"[ERROR] Not valid JSON: {e}")

def read_existing_csv(path):
    rows = []
    if os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                rows.append(row)
    return rows

def write_full_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADERS)
        w.writeheader()
        for row in rows:
            w.writerow(row)

def status_symbol(status):
    s = (status or "").lower()
    if s == "passed":
        return "✅"
    if s == "failed":
        return "❌"
    return "⏭"

def parse_items(doc):
    # Accept {"data":[{attributes:{...}}]}, or {"tests":[...]}, or a root list
    if isinstance(doc, dict) and isinstance(doc.get("data"), list):
        return doc["data"]
    if isinstance(doc, dict) and isinstance(doc.get("tests"), list):
        return [{"attributes": t} for t in doc["tests"]]
    if isinstance(doc, list):
        return [{"attributes": it} for it in doc]
    sys.exit("[ERROR] Could not find items array. Expected 'data' or 'tests'.")

def to_row(item):
    attr = item.get("attributes", {})
    run_at = attr.get("created-at") or attr.get("created_at") or attr.get("run_at") or ""
    run_id = attr.get("run-id") or attr.get("run_id") or ""
    title = (attr.get("title") or "").strip()
    status = attr.get("status") or ""
    retries = attr.get("retries") or 0
    duration = attr.get("run-time") or attr.get("duration_ms") or attr.get("duration") or ""
    try:
        retries = int(retries)
    except Exception:
        retries = 0
    try:
        duration = int(duration) if duration not in ("", None) else ""
    except Exception:
        duration = ""
    return {
        "run_at": run_at,
        "run_id": run_id or run_at,
        "title": title,
        "status": status,
        "retries": str(retries),
        "duration_ms": str(duration) if duration != "" else "",
        "trend_last5": "",
        "is_flaky": "",
        "reasons": "",
    }

def compute_trend_and_flaky(all_rows):
    def parse_dt(s):
        try:
            return datetime.fromisoformat(s.replace("Z","+00:00"))
        except Exception:
            return datetime.min

    # sort per test, compute trend and flags, then resort by time
    all_rows.sort(key=lambda r: (r["title"], parse_dt(r["run_at"])))
    grouped = {}
    for row in all_rows:
        title = row["title"]
        history = grouped.setdefault(title, [])

        prev_syms = [status_symbol(r["status"]) for r in history][-4:]
        cur_sym = status_symbol(row["status"])
        syms = (prev_syms + [cur_sym])[-5:]
        row["trend_last5"] = "".join(syms)

        # durations last5
        cur_dur = int(row["duration_ms"]) if row.get("duration_ms") else None
        dur_list = [int(r["duration_ms"]) for r in history[-4:] if r.get("duration_ms")]
        if cur_dur is not None:
            dur_list.append(cur_dur)

        reasons, score = [], 0
        # R1
        if syms.count("❌") >= 2:
            score += 40
            reasons.append(">1 fail in last5")
        # R3
        retries_int = int(row.get("retries") or 0)
        if row["status"].lower() == "passed" and retries_int > 1:
            score += 20
            reasons.append(">1 retry to pass")
        # R4
        if len(dur_list) >= 3:
            med = statistics.median(dur_list)
            mean = statistics.mean(dur_list)
            std = statistics.pstdev(dur_list) if len(dur_list) >= 2 else 0.0
            spike = (max(dur_list) / med) if med else 0.0
            cov = (std / mean) if mean else 0.0
            if spike >= 5.0 or cov >= 0.6:
                score += 20
                reasons.append("duration instability")

        row["is_flaky"] = "yes" if (score >= 40 or ">1 fail in last5" in reasons) else "no"
        row["reasons"] = "; ".join(reasons)
        history.append(row)

    def parse_dt2(s):
        try:
            return datetime.fromisoformat(s.replace("Z","+00:00"))
        except Exception:
            return datetime.min
    all_rows.sort(key=lambda r: parse_dt2(r["run_at"]))
    return all_rows

def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    in_json, out_csv = sys.argv[1], sys.argv[2]
    doc = load_json(in_json)
    items = parse_items(doc)
    new_rows = [to_row(it) for it in items if it.get("attributes")]
    if not new_rows:
        sys.exit("[ERROR] No test items found to append.")
    merged = read_existing_csv(out_csv) + new_rows
    merged = compute_trend_and_flaky(merged)
    write_full_csv(out_csv, merged)
    print(f"[OK] Updated CSV: {out_csv}  (rows={len(merged)})")

if __name__ == "__main__":
    main()
