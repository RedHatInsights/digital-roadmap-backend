# Data Pipeline Repository Setup

This document is for maintainers of the **data-pipeline-content repository** at `gitlab.cee.redhat.com/rhel-lightspeed/roadmap/data`.

## Overview

The `stamp-deployment-date.py` script needs to be added to the data-pipeline repository to automatically stamp deployment dates on roadmap items.

## Setup Instructions

### 1. Copy the Stamp Script

Copy `stamp-deployment-date-for-data-pipeline.py` from the digital-roadmap-backend repo to your data-pipeline repo:

```bash
# In data-pipeline-content repo
mkdir -p scripts
curl -o scripts/stamp-deployment-date.py \
  https://raw.githubusercontent.com/RedHatInsights/digital-roadmap-backend/main/scripts/stamp-deployment-date-for-data-pipeline.py

chmod +x scripts/stamp-deployment-date.py
```

### 2. Initial Stamp

Run the script once to stamp all existing items:

```bash
python3 scripts/stamp-deployment-date.py data/roadmap_jira.json
```

This will add `deployedDate` to any items that don't already have one.

### 3. Commit the Changes

```bash
git add data/roadmap_jira.json scripts/stamp-deployment-date.py
git commit -m "Add deployment date stamping

- Add stamp-deployment-date.py script
- Stamp existing roadmap items with deployedDate"
git push origin main
```

## Usage

### Automatic (via GitHub Action)

The digital-roadmap-backend repository has a GitHub Action that will automatically:
1. Clone your data-pipeline repo
2. Run the stamp script
3. Commit and push changes

This runs automatically when a release tag is created in the backend repo.

**No action needed on your part** - the automation handles it.

### Manual Usage

If you add new roadmap items manually, you can stamp them:

```bash
# Stamp with today's date
python3 scripts/stamp-deployment-date.py data/roadmap_jira.json

# Stamp with specific date
python3 scripts/stamp-deployment-date.py data/roadmap_jira.json 2026-05-18
```

### Pre-commit Hook (Optional)

You can add a pre-commit hook to automatically stamp new items:

```bash
# .git/hooks/pre-commit
#!/bin/bash
if git diff --cached --name-only | grep -q "data/roadmap_jira.json"; then
    python3 scripts/stamp-deployment-date.py data/roadmap_jira.json
    git add data/roadmap_jira.json
fi
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

## How It Works

The script:
- Reads `data/roadmap_jira.json`
- For each item, checks if `details.deployedDate` exists
- If missing, sets it to the current date (or provided date)
- Writes the updated JSON back to the file
- **Idempotent**: Safe to run multiple times, won't change existing dates

## Example

Before:
```json
{
  "package": "nodejs",
  "details": {
    "type": "addition",
    "dateAdded": "2026-04-15"
  }
}
```

After running script:
```json
{
  "package": "nodejs",
  "details": {
    "type": "addition",
    "dateAdded": "2026-04-15",
    "deployedDate": "2026-05-18"
  }
}
```

## Why This Matters

The notification system uses `deployedDate` to determine which roadmap items are "new" (deployed in last 30 days). Without `deployedDate`, notifications might miss items or include stale ones.

**Before**: Items used `dateAdded` (when loaded from Jira)
- Problem: Item added to Jira on April 1, but not deployed until May 1
- Result: Notification on May 15 thinks item is 45 days old, excludes it

**After**: Items use `deployedDate` (when actually deployed)
- Same item: `dateAdded: 2026-04-01`, `deployedDate: 2026-05-01`
- Result: Notification on May 15 knows item was deployed 14 days ago, includes it

## Questions?

Contact the digital-roadmap-backend team or see:
- `docs/DEPLOYMENT_DATE_STAMPING.md` in backend repo for full architecture
- `.github/workflows/stamp-roadmap-deployment.yml` for automation details
