# STRATA JMLR Submission Status

## Completed

- `manuscript_draft.tex` is on the official JMLR preprint style via `jmlr2e.sty`.
- The manuscript builds locally to `manuscript_draft.pdf` with bibliography resolved.
- Title page requirements are present: running head, corresponding author email/address block, five keywords, and sub-200-word abstract.
- `cover_letter_template.md` has been expanded into a concrete draft with disclosure prompts, suggested action editors, suggested reviewers, and keywords.
- Reproducibility assets exist and have been exercised: code, tests, examples, benchmark scripts, generated outputs, and `scripts/build_submission_bundle.py`.
- Real-data, ablation, fairness, and method-comparison outputs have been generated from current code.
- The manuscript framing now states the real-data result conservatively: transfer across public topologies is supported, but CHMP does not yet show a consistent advantage over Mondrian on those runs.

## Remaining Manual Checks Before Submission

1. Confirm final author metadata exactly as it should appear in JMLR submission fields, especially corresponding-author address details.
2. Confirm the disclosure text before upload:
   - prior-publication or preprint overlap
   - explicit author-consent statement
   - competing-interest statement
   - funding statement
3. Manually review suggested action editors and reviewers for conflicts of interest or recent collaborations.
4. Decide whether to keep the current concise manuscript or add a short appendix/supplement pointer for extra diagnostics and ablations.
5. Do a final visual PDF pass for non-fatal layout issues such as overfull boxes or float placement.

## Verified Project State

- Full test suite: 98 passed.
- Real-data comparison outputs exist for ACTIVSg200 and IEEE 118.
- Supplementary archive can be built and is pruned to avoid recursive packaging artifacts.
- Standalone code repository has been synced, committed, and pushed separately.

## Recommended Final Submission Sequence

1. Rebuild `supplementary.zip` if any manuscript-linked outputs change.
2. Recompile the JMLR PDF after the last text edit.
3. Perform the manual metadata and conflict checks above.
4. Upload manuscript PDF, cover letter, and supplementary materials.
