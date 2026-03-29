"""Generate markdown tables used in the paper from outputs/*.csv.

Creates `paper/tables/*.md` files so the paper can include them or authors
can copy results into LaTeX. Designed to be lightweight and reproducible.
"""
from pathlib import Path
import csv
import statistics

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper" / "tables"
OUT.mkdir(parents=True, exist_ok=True)

def read_csv(path):
    with open(path, newline='') as f:
        return list(csv.DictReader(f))

def fmt_mean_std(values):
    if not values:
        return "-"
    m = statistics.mean(values)
    s = statistics.pstdev(values)
    return f"{m:.3f} ± {s:.3f}"

def baseline_table():
    rows = read_csv(ROOT / 'outputs' / 'baseline_comparison.csv')
    methods = sorted({r['method'] for r in rows})
    lines = ["| Method | Marginal Cov | Mean Width | ECE |",
             "|---|---:|---:|---:|"]
    for m in methods:
        data = [r for r in rows if r['method']==m]
        covs = [float(r['marginal_cov']) for r in data]
        widths = [float(r['mean_width']) for r in data]
        eces = [float(r['ece']) for r in data]
        lines.append(f"| {m} | {fmt_mean_std(covs)} | {fmt_mean_std(widths)} | {fmt_mean_std(eces)} |")
    (OUT / 'baseline.md').write_text('\n'.join(lines))

def full_table():
    rows = read_csv(ROOT / 'outputs' / 'full_comparison.csv')
    methods = sorted({r['method'] for r in rows})
    lines = ["| Method | Marginal Cov | Mean Width | ECE |",
             "|---|---:|---:|---:|"]
    for m in methods:
        data = [r for r in rows if r['method']==m]
        covs = [float(r['marginal_cov']) for r in data]
        widths = [float(r['mean_width']) for r in data]
        eces = [float(r['ece']) for r in data]
        lines.append(f"| {m} | {fmt_mean_std(covs)} | {fmt_mean_std(widths)} | {fmt_mean_std(eces)} |")
    (OUT / 'full_comparison.md').write_text('\n'.join(lines))

def lambda_table():
    p = ROOT / 'outputs' / 'lambda_sensitivity.csv'
    if not p.exists():
        return
    rows = read_csv(p)
    lambdas = sorted({float(r['lambda']) for r in rows})
    lines = ["| Lambda | Coverage | Width | ECE |", "|---:|---:|---:|---:|"]
    for lam in lambdas:
        data = [r for r in rows if float(r['lambda'])==lam]
        covs = [float(r['marginal_cov']) for r in data]
        widths = [float(r['mean_width']) for r in data]
        eces = [float(r['ece']) for r in data]
        lines.append(f"| {lam:.2f} | {fmt_mean_std(covs)} | {fmt_mean_std(widths)} | {fmt_mean_std(eces)} |")
    (OUT / 'lambda_sensitivity.md').write_text('\n'.join(lines))

def alpha_table():
    p = ROOT / 'outputs' / 'alpha_sweep.csv'
    if not p.exists():
        return
    rows = read_csv(p)
    alphas = sorted({float(r['alpha']) for r in rows})
    lines = ["| Alpha | Coverage | Width |", "|---:|---:|---:|"]
    for a in alphas:
        data = [r for r in rows if float(r['alpha'])==a]
        covs = [float(r['marginal_cov']) for r in data]
        widths = [float(r['mean_width']) for r in data]
        lines.append(f"| {a:.3f} | {fmt_mean_std(covs)} | {fmt_mean_std(widths)} |")
    (OUT / 'alpha_sweep.md').write_text('\n'.join(lines))

def main():
    baseline_table()
    full_table()
    lambda_table()
    alpha_table()
    print('Wrote tables to', OUT)

if __name__ == '__main__':
    main()
