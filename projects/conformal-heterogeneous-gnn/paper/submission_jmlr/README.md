Submission folder for JMLR (Journal of Machine Learning Research)

This folder contains the files and instructions needed to prepare a JMLR submission for the STRATA paper.

Checklist (what to assemble before submission):

- manuscript.pdf (PDF typeset using JMLR LaTeX style)
- cover_letter.pdf (or plain text cover letter as PDF)
- supplementary.zip (optional): code, data, additional figures, tables, appendix
- references.bib (BibTeX file used to generate bibliography in manuscript)
- data_provenance.txt (short file describing data sources and licenses; include ACTIVSg200 and MATPOWER citation)

Useful links:
- JMLR author instructions: https://www.jmlr.org/format/authors-guide.html
- JMLR submission system: https://jmlr.csail.mit.edu/manudb/
- JMLR LaTeX style repo: https://github.com/JmlrOrg/jmlr-style-file

Recommended workflow (quick):

1. Install LaTeX (TeX Live / MiKTeX) and `pandoc` if you want to convert from Markdown.
2. Obtain the JMLR style files and follow `authors-guide.html`.
3. Produce `manuscript.pdf` using the JMLR LaTeX style. If you prefer Markdown, you can generate a LaTeX file via `pandoc` and then compile, but verify the output matches JMLR formatting.

Pandoc helper (see `convert_with_pandoc.sh`) will produce a LaTeX file and a draft PDF from `../strata-paper.md` for review; you must still adapt to the JMLR style and run `pdflatex`/`bibtex` as required.

Minimum files to upload to JMLR Manudb:
- `manuscript.pdf`
- `cover_letter.pdf` (or plain text)
- Supplemental archive (zip/tar) containing code and data references

If you want, I will:
- Generate a BibTeX `references.bib` from `REFERENCES.md` (requires time to convert all entries).
- Convert `paper/strata-paper.md` to a LaTeX draft using `pandoc` and place it here as `manuscript.tex` (done below as a draft). 
- Prepare `data_provenance.txt` listing ACTIVSg200 and MATPOWER sources and licenses.


