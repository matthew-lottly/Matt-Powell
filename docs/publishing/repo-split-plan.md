# Repo Split Plan

Use this when you are ready to move project folders into their own public repositories.

## Recommended Split Order

1. `environmental-monitoring-api`
2. `environmental-monitoring-analytics`
3. `monitoring-data-warehouse`

## Why This Order

- The API project is the strongest flagship repo and should anchor your pinned set first.
- The analytics project is lightweight and fast to publish once the API repo is visible.
- The warehouse project rounds out the portfolio by showing database-engineering depth.

## Proposed Repo Names

- `environmental-monitoring-api`
- `environmental-monitoring-analytics`
- `monitoring-data-warehouse`

## Shared Publication Checklist

- Move the project folder contents to the new repository root
- Keep the README concise and role-oriented
- Add one preview asset or screenshot near the top
- Add About description and topics on GitHub
- Verify the setup instructions from a clean checkout
- Enable the repo-specific workflow if CI is present

## Helper Scripts

- [extract-environmental-monitoring-api.ps1](extract-environmental-monitoring-api.ps1)
- [extract-environmental-monitoring-analytics.ps1](extract-environmental-monitoring-analytics.ps1)
- [extract-monitoring-data-warehouse.ps1](extract-monitoring-data-warehouse.ps1)
- [extract-all-projects.ps1](extract-all-projects.ps1)

## Publish Command Guides

- [commands/publish-environmental-monitoring-api.md](commands/publish-environmental-monitoring-api.md)
- [commands/publish-environmental-monitoring-analytics.md](commands/publish-environmental-monitoring-analytics.md)
- [commands/publish-monitoring-data-warehouse.md](commands/publish-monitoring-data-warehouse.md)

## Launch Checklist

- [standalone-launch-checklist.md](standalone-launch-checklist.md)
- [publish-main-portfolio.md](publish-main-portfolio.md)