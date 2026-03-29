#!/usr/bin/env bash
set -euo pipefail

# Converter wrapper for CI: converts the repo markdown to a LaTeX draft using pandoc
MD="../../strata-paper.md"
OUT="manuscript_draft.tex"

if ! command -v pandoc >/dev/null 2>&1; then
  echo 'pandoc not found; skipping conversion'
  exit 0
fi

echo "Converting $MD -> $OUT"
pandoc -s "$MD" -o "$OUT" --wrap=none
echo "Wrote $OUT"
