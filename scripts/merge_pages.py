#!/usr/bin/env python3
import argparse, glob, json, os

p = argparse.ArgumentParser(description='Merge paginated Testomat JSON pages into one {"data": [...]} file.')
p.add_argument('--glob', required=True, help='Glob pattern for pages, e.g. ~/Desktop/testomat_runs/run_c4883898_p*.json')
p.add_argument('--out', required=True, help='Output JSON path')
a = p.parse_args()

files = sorted(glob.glob(os.path.expanduser(a.glob)))
out = {'data': []}
for f in files:
    with open(f, encoding='utf-8') as fh:
        j = json.load(fh)
    out['data'].extend(j.get('data', j.get('tests', [])))

os.makedirs(os.path.dirname(os.path.expanduser(a.out)), exist_ok=True)
with open(os.path.expanduser(a.out), 'w', encoding='utf-8') as w:
    json.dump(out, w, ensure_ascii=False)
print(f'Merged {len(files)} pages -> {a.out}; items={len(out["data"])}')
