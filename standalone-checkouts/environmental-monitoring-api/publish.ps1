param(
    [string]$Owner = "matthew-lottly",
    [string]$Repo = "environmental-monitoring-api"
)

git init
git add .
git commit -m "Initial standalone release"
git branch -M main
git remote add origin "https://github.com/$Owner/$Repo.git"
git push -u origin main