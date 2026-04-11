Repository: environmental-monitoring-api
Priority: First 10
Labels: enhancement, ci, showcase

Title: Improve operational examples, startup validation, and rollback guidance

Body:

Summary
Upgrade `environmental-monitoring-api` so reviewers can see richer payload examples, clearer operational scenarios, and stronger startup and health-check confidence.

Why this matters
This repo reads like a production-leaning monitoring service. The highest-value improvement is to make that operational story more concrete and better tested.

Requested changes
- Add richer example payloads tied to realistic monitoring conditions.
- Add health-check and startup-failure tests.
- Expand the runbook with rollback notes.
- Keep examples aligned with downstream dashboard expectations.

Definition of done
- The API docs and review artifacts show realistic operational payloads.
- Startup and health-check behavior are validated.
- The runbook includes rollback guidance.