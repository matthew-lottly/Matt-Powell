"""Verify manuscript numbers against CSV outputs."""
import pandas as pd

print("=== BASELINE COMPARISON (20 seeds) ===")
df = pd.read_csv("outputs/baseline_comparison.csv")
for m in ["mondrian_cp", "chmp_mean", "chmp_median", "chmp_median_floor"]:
    s = df[df["method"] == m]
    print(f"  {m}: cov={s.marginal_cov.mean():.3f}+/-{s.marginal_cov.std():.3f}"
          f"  w={s.mean_width.mean():.3f}+/-{s.mean_width.std():.3f}"
          f"  ece={s.ece.mean():.3f}+/-{s.ece.std():.3f}")

print("\n=== FULL COMPARISON (20 seeds) ===")
df2 = pd.read_csv("outputs/full_comparison.csv")
for m in df2["method"].unique():
    s = df2[df2["method"] == m]
    print(f"  {m}: cov={s.marginal_cov.mean():.3f}+/-{s.marginal_cov.std():.3f}"
          f"  w={s.mean_width.mean():.3f}+/-{s.mean_width.std():.3f}"
          f"  ece={s.ece.mean():.3f}+/-{s.ece.std():.3f}")

print("\n=== ENSEMBLE (20 seeds) ===")
df3 = pd.read_csv("outputs/ensemble_comparison.csv")
s = df3[df3["method"] == "ensemble_cp"]
print(f"  ensemble_cp: cov={s.marginal_cov.mean():.3f}+/-{s.marginal_cov.std():.3f}"
      f"  w={s.mean_width.mean():.3f}+/-{s.mean_width.std():.3f}"
      f"  ece={s.ece.mean():.3f}+/-{s.ece.std():.3f}")

print("\n=== REAL DATA (3 seeds each) ===")
df4 = pd.read_csv("outputs/real_method_comparison.csv")
for ds in ["ACTIVSg200", "IEEE118"]:
    for meth in ["mondrian", "chmp"]:
        s = df4[(df4["dataset"] == ds) & (df4["method"] == meth)]
        print(f"  {ds} {meth}: cov={s.marginal_cov.mean():.3f}"
              f"  w={s.mean_width.mean():.3f}"
              f"  ece={s.ece.mean():.3f}")

print("\n=== LAMBDA SENSITIVITY (20 seeds) ===")
df5 = pd.read_csv("outputs/lambda_sensitivity.csv")
for lam in [0.0, 0.1, 0.3, 0.5, 1.0]:
    s = df5[df5["lambda"] == lam]
    print(f"  lambda={lam}: cov={s.marginal_cov.mean():.3f}+/-{s.marginal_cov.std():.3f}"
          f"  w={s.mean_width.mean():.3f}+/-{s.mean_width.std():.3f}"
          f"  ece={s.ece.mean():.3f}+/-{s.ece.std():.3f}")
