# Merge Checklist

Use this before merging a broad backlog or cleanup branch.

1. Review the branch diff against `main` for accidental unrelated changes.
2. Confirm repo-hub changes stay in the hub and project-source changes stay in standalone repos.
3. Verify `README.md`, `things-to-do.md`, `ROADMAP.md`, and `docs/portfolio-matrix.md` are aligned.
4. Confirm generated caches, `node_modules`, and build outputs are not staged.
5. Check whether any work should be split into a smaller follow-up PR.
6. Verify the showcase set still reflects the best public-facing projects.
7. Push only after the working tree is clean and the remaining follow-up items are documented.