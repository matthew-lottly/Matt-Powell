**TMLR Repository Submission Template (minimal)**

Repository structure recommended for submission (minimal):

- `README.md` — quickstart and reproduction commands (1–2 commands to reproduce main results).
- `paper/` — LaTeX source and final PDF (`paper.tex`, `paper.pdf`).
- `src/` — source code (package layout).
- `experiments/` — scripts to run experiments and produce figures/tables.
- `requirements.txt` or `environment.yml` — exact dependencies.
- `run_experiment.sh` — single script reproducing main table/figure.
- `LICENSE` — OSI approved (MIT/Apache/BSD).
- `CITATION.cff` — citation metadata.
- `README-repro.md` — detailed reproduction instructions (datasets, expected runtimes, hardware requirements, seeds).
- `release/` — optional: zipped model weights or small artifacts, or links in `README-repro.md`.

Cover letter template (short):

Dear Editors,

We submit "<Title>" for consideration in Transactions on Machine Learning Research. The manuscript introduces [one-sentence contribution]. The code and reproduction materials are available at: <GitHub repo URL> (tag: `v1.0-submission`). We have prepared an anonymized manuscript for double-blind review. All code is open-source under the <license> license. No authorship fees are required.

Sincerely,
[Corresponding author]

Quick reproducibility commands to include in `README.md`:

```bash
git clone <repo>
cd <repo>
pip install -r requirements.txt
bash run_experiment.sh
```

If you want, I can create a draft `README.md`, a `CITATION.cff`, and a simple `run_experiment.sh` that runs a small smoke test for your project.
