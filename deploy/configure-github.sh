#!/bin/sh
# Run locally with an already authenticated GitHub CLI. Secret values go via stdin.
set -eu
[ "$#" -eq 2 ] || { echo 'Usage: configure-github.sh PRIVATE_KEY VERIFIED_KNOWN_HOSTS' >&2; exit 2; }
repo=studiobaff/dronemissions
gh auth status
gh secret set DRONEMISSIONS_DEPLOY_KEY --repo "$repo" < "$1"
gh secret set DRONEMISSIONS_KNOWN_HOSTS --repo "$repo" < "$2"
gh variable set DEPLOY_ENABLED --body false --repo "$repo"
echo 'Secrets saved. Deployment remains disabled until the reviewed UI and deployment PRs are merged.'
