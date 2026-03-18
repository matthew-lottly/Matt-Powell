# Publish Main Portfolio Repository

Use this file to push the main `Matt-Powell` portfolio repository after the README, docs, and project folders are in the state you want publicly visible.

## Repository Settings

- Repository: `Matt-Powell`
- Owner: `matthew-lottly`
- Remote: `https://github.com/matthew-lottly/Matt-Powell.git`

## GitHub About Box

- Description: `Portfolio repository for backend, GIS, frontend, database, and analytics engineering work.`
- Website: `https://lottly-ai.com/`
- Topics: `portfolio`, `software-engineering`, `gis`, `geospatial`, `frontend`, `python`, `sql`, `data-engineering`, `backend`

## Push Commands

```powershell
Set-Location d:\GitHub
git status --short
git add README.md docs .github projects standalone-repos
git commit -m "Finalize portfolio launch materials"
git push -u origin main
```

If Git reports there is nothing to commit, skip the `git commit` line and run:

```powershell
git push -u origin main
```

## After Push

1. Confirm [README.md](../README.md) renders correctly on GitHub.
2. Add the About box settings above in the GitHub repository sidebar.
3. Confirm the workflow badges and relative project links render correctly.
4. Pin `Matt-Powell` fifth, after the four standalone repositories are live.

## Recommended Sequence

1. Push `Matt-Powell` first so the portfolio hub is live.
2. Publish the four standalone repositories using [standalone-launch-checklist.md](standalone-launch-checklist.md).
3. Revisit the pinned repositories and About sections after all five repositories are public.