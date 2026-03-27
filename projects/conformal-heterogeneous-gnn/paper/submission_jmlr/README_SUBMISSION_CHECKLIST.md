Quick submission checklist (JMLR)

1. Convert `paper/strata-paper.md` to LaTeX using the JMLR style files. Recommended: clone https://github.com/JmlrOrg/jmlr-style-file and follow the authors guide.
2. Make sure manuscript PDF < 5 MB (JMLR limit) or contact editorial office for large files; include large supplementary data as external archive.
3. Prepare `cover_letter.pdf` (use `cover_letter_template.md`), and suggest 3-5 action editors and 3-5 potential reviewers.
4. Create `supplementary.zip` containing:
   - `code/` (all scripts to reproduce core experiments)
   - `data_provenance.txt` (this file)
   - `README.md` for reproduction instructions
   - `outputs/` sample PNGs and CSV summary tables
5. Prepare `references.bib` and ensure citations compile.
6. Upload to https://jmlr.csail.mit.edu/manudb/

If you want, I can:
- Generate a first-pass `manuscript_pandoc.tex` and PDF using `convert_with_pandoc.sh`.
- Attempt to produce a `references.bib` by converting `REFERENCES.md` entries into BibTeX (will take a little time to verify each entry).
