Repository: spatial-data-api
Priority: First 10
Labels: enhancement, ci, showcase

Title: Add richer API examples, rollback notes, and invalid-query coverage

Body:

Summary
Strengthen the reviewability and operational confidence of `spatial-data-api` by expanding the concrete API examples, documenting rollback guidance, and adding failure-path validation for invalid spatial query parameters.

Why this matters
This repo is one of the clearest backend and GIS signals in the portfolio. The next quality jump is stronger evidence that the API is understandable, stable, and safer to operate.

Requested changes
- Add at least one richer request and response example to the review artifacts.
- Add rollback or recovery guidance to the runbook.
- Add tests for at least one invalid bbox or invalid filter scenario.
- Keep README wording outcome-focused rather than implementation-heavy.

Definition of done
- A reviewer can see realistic request and response examples without running the service.
- The runbook contains rollback guidance.
- Failure-path validation exists for invalid spatial queries.