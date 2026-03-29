# STRATA Project Status and Todo List

## Where the project is at

STRATA is past the exploratory stage and is already in paper-packaging mode.

- The manuscript draft is substantially complete, with abstract, methods, experiments, results, discussion, conclusion, and a 66-item reference list.
- A compiled JMLR-style draft already exists in `paper/submission_jmlr/manuscript_draft.pdf`.
- The supplementary bundle contains publication-oriented artifacts, including baseline, advanced, lambda, alpha, and full comparison tables plus figure outputs.
- Synthetic multi-seed benchmarking is already summarized in `summary.json`, `baseline_table.md`, `advanced_table.md`, and `full_comparison_table.md`.
- The main synthetic result pattern is coherent: Mondrian remains strongest on ECE, CHMP mostly redistributes interval width rather than reducing it, and the ensemble variant is the only method showing a clearly narrower mean width.
- Real-data benchmarking exists for ACTIVSg200 and IEEE118, but the visible root-level outputs suggest lighter coverage there than for the synthetic study.
- Diagnostic artifacts already exist for fairness, conditional coverage, width deciles, bootstrap confidence intervals, and statistical significance testing.
- Profiling artifacts also exist, which means the project has enough implementation maturity to justify a pass on runtime and reproducibility cleanup.
- The biggest remaining risk is not missing experiments in the absolute sense; it is mismatch between what the paper claims, what the visible artifacts substantiate, and how clearly the paper explains those claims.
- The paper also still needs a stronger editorial pass on figure captions, cross-references, logical sequencing, and citation support for a few ambitious statements.

## 40 project todos

1. [x] Verify that every numeric value in Tables 1 through 6 matches the latest generated table artifacts in the supplementary bundle.
2. [x] Reconcile the metric differences between the markdown manuscript tables and `paper/submission_jmlr/supplementary_bundle/outputs/summary.json`.
3. [x] Decide which result set is the canonical source of truth for the paper: manuscript markdown tables, supplementary markdown tables, or JSON summaries.
4. [ ] Add a short reproducibility note stating which script regenerates every table and figure used in the manuscript.
5. [ ] Create a one-page experiment inventory mapping each paper claim to its backing output file.
6. [ ] Confirm that the reported 20-seed synthetic experiments are reproducible from the current code and not from an older run configuration.
7. [ ] Check whether all nine methods in the full comparison were run under identical train-calibration-test splits across seeds.
8. [ ] Confirm the exact default hyperparameters for CHMP, MetaCalibrator, AttentionCalibrator, LearnableLambda, CQR, and Ensemble.
9. [x] Add one concise paragraph clarifying why width redistribution is operationally useful even when aggregate width barely changes.
10. [x] Tighten the abstract so it reflects the strongest supported claim without overselling CHMP as a width-reduction method.
11. [x] Tighten the introduction so the problem statement is clearly about topology-aware valid uncertainty, not raw predictive superiority.
12. [ ] Add a short contribution statement that distinguishes framework contributions from empirical performance contributions.
13. [ ] Rework the methods section headings so the reader sees backbone model, calibration method, advanced variants, and diagnostics in a cleaner sequence.
14. [ ] Add a compact notation table for symbols such as $\alpha$, $\hat{q}$, $\sigma_i$, $r_i$, and $\mathcal{D}_{\text{cal}}$.
15. [ ] Review the theorem statement and proof sketch for mathematical precision and match it against the exact implementation assumptions.
16. [ ] Check whether the phrase "type-conditional coverage" is always used accurately rather than implying full conditional coverage.
17. [ ] Audit the wording around exchangeability to ensure the limitations section fully matches the claims made in the methods section.
18. [ ] Add an implementation paragraph explaining how training residuals are frozen and stored before calibration begins.
19. [ ] Document how isolated nodes or low-degree nodes are handled when neighbor-derived difficulty is sparse.
20. [ ] Expand the experimental setup with exact split proportions, random seed policy, and any early stopping criteria.
21. [ ] State the hardware and approximate runtime for baseline, advanced calibrator, and ensemble experiments.
22. [ ] Turn the profiling artifact into one short sentence about current performance bottlenecks and whether optimization matters for submission.
23. [x] Make the real-data section explicit about how much of ACTIVSg200 and IEEE118 is truly real versus synthetically derived.
24. [ ] Add a small table or appendix note comparing synthetic and real-data evaluation scope side by side.
25. [x] Check whether the paper should discuss IEEE118 more directly instead of letting it appear only in output files.
26. [ ] Decide whether fairness auditing is core to the paper or only a supplementary diagnostic, then align the text accordingly.
27. [ ] Add one sentence explaining what "fairness" means in this infrastructure context if the audit remains in scope.
28. [ ] Review whether conditional coverage analysis should be promoted into the main text rather than kept implicit in diagnostics.
29. [x] Add a short explanation for why CQR underperforms here and whether that is architectural, optimization-related, or data-related.
30. [x] Check whether the ensemble result should be presented as the best empirical performer while CHMP is framed as the main conceptual contribution.
31. [ ] Make the limitations section sharper by separating evidence-backed limitations from forward-looking speculation.
32. [ ] Add a paragraph on external validity and what kinds of real infrastructure datasets would be needed next.
33. [ ] Decide whether the scalability section needs a small synthetic stress test or whether it should remain explicitly future work.
34. [ ] Review the diagnostics section and confirm that each named diagnostic has either a shown output or an explicit note that results are supplementary.
35. [ ] Check that all output artifact names are stable and submission-safe rather than temporary or development-oriented.
36. [ ] Clean up any ambiguity between `ACTIVSg200`, `ACTIVSg200 200-bus`, and other naming variants across the manuscript.
37. [ ] Add a brief paragraph describing exactly how telecom and water layers are constructed from the power topology in the real-data benchmark.
38. [x] Make sure the conclusion does not imply stronger real-world validation than the current artifacts actually support.
39. [ ] Add a final editorial pass for redundancy across the abstract, discussion, and conclusion so the same claim is not repeated three times.
40. [ ] Prepare a submission-readiness checklist covering manuscript, supplementary bundle, code reproducibility, and artifact regeneration.

## 10 citation, reference, caption, and logic todos

41. [x] Audit every in-text citation for necessity and make sure each citation supports the exact sentence it is attached to rather than the paragraph broadly.
42. [x] Double-check that all references cited in the introduction and related work are present in the reference list and correctly numbered.
43. [x] Add a few more citations around graph-dependent conformal prediction and uncertainty on heterogeneous graphs if stronger prior-art positioning is needed.
44. [ ] Add one or two stronger citations around infrastructure interdependency modeling to support the motivating examples in the introduction.
45. [x] Review whether the fairness and broader-impact discussion needs additional citations from infrastructure equity or risk-allocation literature.
46. [x] Replace the current figure labels near the top of the manuscript with full descriptive captions that explain what the reader should notice in each figure.
47. [x] Add captions that explicitly state dataset, method subset, seed count, and the take-away for every main figure.
48. [ ] Check that every figure mentioned in the manuscript is referenced in logical reading order and appears near the paragraph that interprets it.
49. [ ] Review the paper section by section for logical flow so each result answers a question raised earlier in the methods or setup.
50. [ ] Do a final claim-to-citation-to-figure pass where every major claim is backed by at least one result artifact, one figure or table, or one citation.