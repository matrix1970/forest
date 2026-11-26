# PowerShell script to perform git add, commit, pull (rebase) and push for the forest repo.
# Save as push_forest.ps1 in the repository root.
param(
    [Parameter(Mandatory=$true)]
    [string]$Site
)

# Change to repository root (the script assumes it's placed inside the repo)
$repoRoot = (git rev-parse --show-toplevel)
Set-Location $repoRoot

# Stage all changes
git add .

# Build commit message with timestamp
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$commitMsg = "Update $Site report $timestamp"

# Commit (ignore if nothing to commit)
try {
    git commit -m $commitMsg
} catch {
    Write-Host "No changes to commit."
}

# Pull with rebase
git pull --rebase origin main

# Push with force‑with‑lease
git push --force-with-lease origin main
