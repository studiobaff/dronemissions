#!/bin/sh
# Run locally with an already authenticated GitHub CLI. Secret values go via stdin.
set -eu
[ "$#" -eq 4 ] || { echo 'Usage: configure-github.sh PRIVATE_KEY VERIFIED_KNOWN_HOSTS DEPLOY_TARGET(user@host) SITE_URL' >&2; exit 2; }
repo=$(gh repo view --json nameWithOwner -q .nameWithOwner)
gh auth status
gh secret set DRONEMISSIONS_DEPLOY_KEY --repo "$repo" < "$1"
gh secret set DRONEMISSIONS_KNOWN_HOSTS --repo "$repo" < "$2"
gh variable set DRONEMISSIONS_DEPLOY_TARGET --body "$3" --repo "$repo"
gh variable set DRONEMISSIONS_SITE_URL --body "$4" --repo "$repo"
gh variable set DEPLOY_ENABLED --body false --repo "$repo"
echo 'Secrets and variables saved. Deployment stays disabled until DEPLOY_ENABLED is set to true.'
