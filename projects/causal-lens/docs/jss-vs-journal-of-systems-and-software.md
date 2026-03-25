# JSS vs. Journal of Systems and Software for CausalLens

This note compares the two venues that came up during manuscript planning.

## Scope Note

The JSS side of this comparison is based on the journal pages verified on 2026-03-25 and the repository's current JSS readiness note.

The Journal of Systems and Software author-guide URL blocked automated retrieval with HTTP 403 during the same session. Because of that, the Journal of Systems and Software side below is a scope-based comparison rather than a line-by-line guide verification. Before any submission there, the live author guide should be manually rechecked.

## Short Answer

JSS is the better fit for the current CausalLens paper.

Journal of Systems and Software would require a materially different paper.

## Comparison

| Dimension | JSS | Journal of Systems and Software |
|---|---|---|
| Core question | What statistical methods does the package implement, and how does the software support their use and replication? | What software-engineering or systems contribution does the work make, and how is it evaluated as a software system? |
| Best CausalLens framing | Statistical software integrating multiple causal designs with diagnostics and replication support | Engineered analytics platform or software architecture for causal-analysis workflows |
| Evidence reviewers will care about most | Methods coverage, validation, replication, benchmark outputs, comparison with related statistical software | Architecture, design rationale, maintainability, testing strategy, engineering tradeoffs, possibly user or performance evaluation |
| Current repository strengths | Public code, tests, replication scripts, benchmark outputs, JSS-style manuscript draft, software comparisons | Decent engineering hygiene, but limited explicit systems-style evaluation |
| Main current weakness | Final manuscript polish and exact submission packaging | Paper is not presently framed as a software-engineering systems contribution |
| Rewrite burden from current draft | Moderate finishing work | Major repositioning work |

## Why JSS Fits Better Right Now

The current manuscript draft is built around four things:

1. implemented causal estimators and diagnostics
2. comparison with related causal-inference software
3. benchmark and replication evidence
4. a reproducible software-paper workflow

That is exactly the center of gravity for a statistical-software submission.

## What Would Need to Change for Journal of Systems and Software

If you wanted to target Journal of Systems and Software instead, the paper would need to shift emphasis away from estimator validation and toward software engineering. In practice, that would likely require:

1. a stronger architecture section with module boundaries, design patterns, and extension mechanisms
2. explicit engineering evaluation such as maintainability, testability, reliability, portability, or performance evidence
3. a clearer software-engineering problem statement beyond "causal workflows are fragmented"
4. less space on econometric background and more space on software design decisions and tradeoffs
5. stronger discussion of development workflow, release engineering, and possibly user-facing evaluation

## Recommendation

Use JSS as the primary submission path for the current paper.

Treat Journal of Systems and Software as a different-paper option, not as a minor formatting variant of the same draft.
