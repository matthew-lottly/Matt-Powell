#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
cd paper/submission_jmlr

echo "Building LaTeX manuscript..."
pdflatex -interaction=nonstopmode manuscript_draft.tex || true
bibtex manuscript_draft || true
pdflatex -interaction=nonstopmode manuscript_draft.tex || true
pdflatex -interaction=nonstopmode manuscript_draft.tex || true

echo "Built: manuscript_draft.pdf"
