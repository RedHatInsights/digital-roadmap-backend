# Deployment Date Stamping

## Overview

Roadmap items need a `deployedDate` field to track when they were first deployed to production. This is used by the notification system to identify "new" items in the last 30 days.

## Architecture

Instead of stamping dates during container builds (which would be lost on the next data pull), we stamp them **at the source** in the data-pipeline-content repository.

### How It Works

1. **Source Repository**: `roadmap_jira.json` lives in the data-pipeline-content repo at GitLab
2. **Stamp Script**: `stamp-deployment-date.py` lives in data-pipeline repo (copied from this repo)
3. **Automation**: GitHub Action workflow runs on release tags and automatically stamps new items
4. **Container Build**: Simply downloads the pre-stamped `roadmap_jira.json`

### Workflow

```
┌─────────────────────────────────────────────────────────┐
│ 1. Create release tag in digital-roadmap-backend        │
│    $ git tag 2026-05-18.01                              │
│    $ git push origin 2026-05-18.01                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 2. GitHub Action triggers automatically                 │
│    - Clones data-pipeline-content repo                  │
│    - Runs stamp script on roadmap_jira.json            │
│    - Commits and pushes changes back                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Container build pulls stamped data                   │
│    - Downloads roadmap_jira.json (already stamped)      │
│    - All items have deployedDate                        │
│    - No additional processing needed                    │
└─────────────────────────────────────────────────────────┘
```

## Setup

### Prerequisites

1. **GitLab Access Token** with write permissions to `gitlab.cee.redhat.com/rhel-lightspeed/roadmap/data`
   - Go to GitLab → Preferences → Access Tokens
   - Create token with `api` and `write_repository` scopes
   - Save token securely

2. **GitHub Secret Configuration**
   - Go to GitHub repo → Settings → Secrets and variables → Actions
   - Add new repository secret: `GITLAB_TOKEN`
   - Paste the GitLab access token

### Files

- **`.github/workflows/stamp-roadmap-deployment.yml`** - GitHub Action workflow
- **`scripts/stamp-deployment-date-for-data-pipeline.py`** - Stamp script (to be copied to data-pipeline repo)

## Usage

### Automatic (Recommended)

When you create a release tag, the workflow automatically runs:

```bash
# Tag the release
git tag 2026-05-18.01
git push origin 2026-05-18.01

# GitHub Action runs automatically
# Check Actions tab in GitHub to see progress
```

### Manual Trigger

You can manually trigger the workflow from GitHub:

1. Go to Actions → "Stamp Roadmap Deployment Dates"
2. Click "Run workflow"
3. Optionally specify a custom date (YYYY-MM-DD)
4. Click "Run workflow" button

### Local Testing

To test the stamp script locally:

```bash
# Clone data-pipeline repo
git clone https://gitlab.cee.redhat.com/rhel-lightspeed/roadmap/data.git

# Copy stamp script
cp scripts/stamp-deployment-date-for-data-pipeline.py data/stamp-deployment-date.py

# Run stamp script
cd data
python3 stamp-deployment-date.py data/roadmap_jira.json

# Review changes
git diff data/roadmap_jira.json
```

## Stamp Script Details

The `stamp-deployment-date.py` script:

- ✅ Only stamps items that **don't already have** a `deployedDate`
- ✅ Preserves existing `deployedDate` values (idempotent)
- ✅ Uses today's date by default, or accepts custom date as argument
- ✅ Returns count of items stamped

### Example Output

```
Stamped 3 roadmap items with deployment date: 2026-05-18

Updated data/roadmap_jira.json
Please commit and push these changes to preserve the deployment dates.
```

## Troubleshooting

### Workflow fails with "Authentication failed"

- Check that `GITLAB_TOKEN` secret is set correctly in GitHub
- Verify token has not expired
- Ensure token has `api` and `write_repository` scopes

### No items were stamped

This is normal if all items already have `deployedDate`. The workflow will:
- Still run successfully
- Report "0 items stamped"
- Not create a commit

### Want to re-stamp an item

Manually remove the `deployedDate` field from that item in `roadmap_jira.json`, then run the workflow again.

## Migration from Old Approach

**Old approach** (in commit 9863763):
- Stamp during Containerfile build
- Problem: stamps lost on next data pull

**New approach** (this document):
- Stamp in data-pipeline repo before deployment
- Stamps persisted in source of truth

To migrate:
1. Remove stamp script integration from Containerfile
2. Set up GitHub Action with GITLAB_TOKEN secret
3. Run workflow once to stamp existing items
4. Future releases will auto-stamp new items

## Related

- RSPEED-2866: Filter roadmap notifications by `deployedDate` instead of `dateAdded`
- See `src/notificator/lifecycle.py` for notification implementation
