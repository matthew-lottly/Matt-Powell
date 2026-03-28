**TMLR Submission Checklist (quick)**

Use this checklist to prepare a submission to Transactions on Machine Learning Research (TMLR). TMLR does not charge APCs; you may submit as an independent author. Follow the official author guide for format details: https://jmlr.org/tmlr/author-guide.html

- **Manuscript**
  - Final PDF and source (LaTeX) ready.
  - Title, abstract (concise), keywords, and clear contribution statements.
  - Ensure the manuscript conforms to TMLR length and formatting (see author guide).

- **Anonymization**
  - TMLR uses double-blind review: prepare an anonymized version (remove names, affiliations, funding acknowledgements) and a separate non-anonymized final version for upload if required after acceptance.

- **Supplementary materials**
  - Clear instructions for reproducing key experiments (scripts/commands).
  - Environment spec: `requirements.txt` or `environment.yml`, Python version, CUDA if needed.
  - Random seeds and deterministic run instructions (single script to reproduce main table/figure): `run_experiment.sh` or `run_all.sh`.
  - Pretrained model weights (if small) or reproducible training script; if large, provide checkpoint download link and MD5.

- **Code repository**
  - Public GitHub repository with permissive OSI-approved license (MIT/BSD/Apache) required by many venues — TMLR does not force license but reproducibility requires open code.
  - Include `README.md` with minimal quickstart: install, run a single experiment, expected outputs.
  - Tag a release matching the submission version (e.g., `v1.0-submission`).

- **Archival / DOI**
  - Prepare to archive the GitHub release on Zenodo (creates DOI). You may wait until acceptance, but preparing metadata speeds publication.

- **Metadata & Licenses**
  - Add `CITATION.cff` (recommended) and choose an OSI-approved license.

- **Ethics / Data**
  - If using external datasets, include download scripts and licensing/usage notes.
  - If using proprietary tools or data, note that reviewers may have trouble reproducing results; prefer free/open datasets and tools.

- **Cover letter / submission notes**
  - Short cover letter stating contribution, relation to prior work, and reproducibility materials location.
  - Declare conflicts of interest, suggested/undesired reviewers if requested.

- **Checks before submission**
  - Confirm no APCs or fees (TMLR: none).
  - Confirm anonymized manuscript ready for double-blind review.
  - Ensure reproducibility script runs in a fresh environment (CI or local test).

---

If you want, I can populate a sample `README.md`, `CITATION.cff`, and a minimal `run_experiment.sh` for your repo next.
