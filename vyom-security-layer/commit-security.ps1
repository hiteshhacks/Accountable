$ErrorActionPreference = "Stop"

# 1. Locate repository.
$root = git rev-parse --show-toplevel
if ($LASTEXITCODE -ne 0 -or !$root) {
    throw "Run this script inside your VYOM+ security Git repository."
}
Set-Location $root

# 2. Require a named branch and create a backup branch when HEAD exists.
$branch = git branch --show-current
if (!$branch) {
    throw "Checkout a branch first."
}

$backup = $null
$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
git rev-parse --verify HEAD 1>$null 2>$null
$hasHead = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $previousErrorActionPreference
if ($hasHead) {
    $backup = "backup/security-before-commits-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    git branch $backup
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create backup branch."
    }
} else {
    Write-Host "No existing commits on '$branch'; skipping backup branch because there is no HEAD to back up."
}

# 3. Collect changed files, then normalize the index so feature grouping is exact.
$files = @(
    git diff --name-only
    git diff --cached --name-only
    git ls-files --others --exclude-standard
) | Where-Object { $_ } | Sort-Object -Unique

if (!$files) {
    Write-Host "No changes to commit."
    exit 0
}

$staged = @(git diff --cached --name-only)
if ($staged.Count) {
    Write-Host "Unstaging existing staged files so commits can be grouped safely."
    if ($hasHead) {
        git reset --mixed
    } else {
        git rm --cached -r -- . 1>$null
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Could not unstage existing files."
    }
}

# Avoid committing credentials, private keys, local databases, caches, or generated test data.
# Keep .env.example commit-eligible because it is a template.
$secretPattern = '(^|/)\.env$|(^|/)\.env\.(?!example$)[^/]+$|(^|/)(id_rsa|id_ed25519)$|(^|/)[^/]*\.(pem|p12|pfx|key)$'
$generatedPattern = '(^|/)(\.pytest_cache|\.pytest_tmp|\.test_runs|__pycache__|logs|dist|build)(/|$)|\.(pyc|pyo|db)$'

$blocked = @($files | Where-Object { $_ -match $secretPattern -or $_ -match $generatedPattern })
$files = @($files | Where-Object { $_ -notmatch $secretPattern -and $_ -notmatch $generatedPattern })

if ($blocked.Count) {
    Write-Host "Skipped generated or potentially sensitive files:"
    $blocked | ForEach-Object { Write-Host "  $_" }
}

if (!$files.Count) {
    Write-Host "No commit-eligible changes remain after filtering."
    exit 0
}

# 4. Group files into feature commits.
# Whole files are grouped by path/name. Mixed changes may need manual staging.
$groups = @(
    @{ Message = "feat(auth): implement JWT authentication"; Pattern = '(^|/)(auth|authentication|jwt|token)(\.|/|$)|(^|/)app/security\.py$|(^|/)scripts/create_user\.py$' },
    @{ Message = "feat(authz): implement RBAC and tenant isolation"; Pattern = 'authoriz|permission|(^|/)rbac|tenant|organization|org_scope|(^|/)app/demo_users\.py$|seed_demo_users' },
    @{ Message = "feat(validation): harden invoice and upload inputs"; Pattern = 'valid|schema|input|gstin|invoice|ingestion|upload' },
    @{ Message = "feat(ai): validate LLM boundary outputs"; Pattern = 'llm|classification|prompt' },
    @{ Message = "feat(gst): add deterministic GST rules"; Pattern = 'gst|tax' },
    @{ Message = "feat(audit): record security events"; Pattern = 'audit|security.?log' },
    @{ Message = "feat(pipeline): integrate security validation pipeline"; Pattern = 'pipeline|test_pipeline' },
    @{ Message = "test(security): add regression coverage"; Pattern = '(^|/)tests/' },
    @{ Message = "docs(security): document controls and testing"; Pattern = '(^|/)docs/|README|TESTING|\.env\.example|pytest\.ini|requirements|\.gitignore' }
)

$assigned = @{}
$commitCount = 0

foreach ($group in $groups) {
    $selected = @($files | Where-Object {
        !$assigned.ContainsKey($_) -and $_ -match $group.Pattern
    })

    if (!$selected.Count) {
        continue
    }

    Write-Host "`nFiles for: $($group.Message)"
    $selected | ForEach-Object { Write-Host "  $_" }

    git add -- $selected
    if ($LASTEXITCODE -ne 0) {
        throw "Could not stage files."
    }

    git diff --cached --check
    if ($LASTEXITCODE -ne 0) {
        throw "Whitespace check failed. Review staged changes."
    }

    git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) {
        continue
    }

    git diff --cached --stat
    $confirm = Read-Host "Create this commit? Type YES to continue"
    if ($confirm -cne "YES") {
        git reset
        if ($LASTEXITCODE -ne 0) {
            throw "Could not unstage files."
        }
        Write-Host "Stopped safely. Remaining changes are preserved."
        break
    }

    git commit -m $group.Message
    if ($LASTEXITCODE -ne 0) {
        throw "Commit failed."
    }

    foreach ($file in $selected) {
        $assigned[$file] = $true
    }
    $commitCount++
}

# 5. Commit remaining files together after review.
$remaining = @($files | Where-Object { !$assigned.ContainsKey($_) })

if ($remaining.Count) {
    Write-Host "`nRemaining files:"
    $remaining | ForEach-Object { Write-Host "  $_" }

    git add -- $remaining
    if ($LASTEXITCODE -ne 0) {
        throw "Could not stage remaining files."
    }

    git diff --cached --check
    if ($LASTEXITCODE -ne 0) {
        throw "Whitespace check failed. Review staged changes."
    }

    git diff --cached --stat
    $confirm = Read-Host "Commit remaining changes together? Type YES"
    if ($confirm -ceq "YES") {
        git commit -m "chore(security): include remaining implementation changes"
        if ($LASTEXITCODE -ne 0) {
            throw "Commit failed."
        }
        $commitCount++
    } else {
        git reset
        if ($LASTEXITCODE -ne 0) {
            throw "Could not unstage remaining files."
        }
        Write-Host "Remaining changes preserved without committing."
    }
}

Write-Host "`nCreated $commitCount commit(s)."
if ($backup) {
    Write-Host "Backup branch: $backup"
} else {
    Write-Host "Backup branch: not created; repository had no prior commits."
}
Write-Host "`nRecent history:"
git log -10 --format="%h %ad %s" --date=iso-local
Write-Host "`nWorking tree:"
git status --short
