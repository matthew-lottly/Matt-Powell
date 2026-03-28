#!/usr/bin/env bash
# Helper: convert the Markdown draft to LaTeX and a draft PDF for review using pandoc.
# Requirements: pandoc, a LaTeX distribution (pdflatex), and optionally bibtex for references

set -e
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="${BASE_DIR}/.."
INPUT_MD="${ROOT_DIR}/strata-paper.md"
OUT_TEX="${BASE_DIR}/manuscript_pandoc.tex"
OUT_PDF="${BASE_DIR}/manuscript_pandoc.pdf"

pandoc "$INPUT_MD" -s -o "$OUT_TEX" --standalone --toc --number-sections --lua-filter=./pandoc_filters/include_figures.lua
# Compile to PDF (may require multiple passes for citations)
pdflatex -interaction=nonstopmode -halt-on-error -output-directory "$BASE_DIR" "$OUT_TEX" || true
bibtex "${BASE_DIR}/manuscript_pandoc" || true
pdflatex -interaction=nonstopmode -halt-on-error -output-directory "$BASE_DIR" "$OUT_TEX" || true
pdflatex -interaction=nonstopmode -halt-on-error -output-directory "$BASE_DIR" "$OUT_TEX" || true

echo "Draft PDF written to: $OUT_PDF"
