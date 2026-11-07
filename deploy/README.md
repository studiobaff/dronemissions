# GitHub → production web deployment

This PR adds deployment infrastructure only. Claude's UI branch is independent; no
application file is changed by this PR. Merge the finished UI into `main` before
enabling deployment. In particular, `main` must contain the current production
features and `dm_migrate()` before its first publication. Do not deploy the older
main branch over the current server.

## Flow

* PRs targeting main: PHP and JS syntax checks, parser tests, release allowlist
  tests and a disposable SQLite/HTTP release-switching test. PR jobs have no SSH
  secret or deployment permission. The existing full application integration
  suite remains a separate review requirement; these checks are not a full
  end-to-end application test.
* Pushes to main affecting web/deploy files: checks first, then production deploy.
  `workflow_dispatch` republishes the current main commit after the same checks.
* `DEPLOY_ENABLED` must equal `true`. Missing/false deliberately disables deploy.
  Set it only after both the reviewed UI and deployment PR have merged.
* Only `dronemissions/public/` is packaged, with full commit and SHA-256 manifest.
  Private state, bridge, documentation and setup tools are never published.
* GitHub pins the existing SSH host key, uses a separate Ed25519 identity and
  sends the ZIP to a fixed forced-command receiver. No rsync delete or repository
  checkout occurs inside the production webroot.
* Server locks deployments, checks paths, hashes, syntax and sizes, backs up the
  active SQLite DB with `VACUUM INTO` plus private configuration, creates a fresh
  release and atomically switches the webroot symlink. Existing immutable originals,
  cache and sessions remain at their existing private location. This is not a new
  full backup of blobs: keep the regular off-server database+blobs backups.
* The receiver checks the served commit and homepage via HTTPS, reverting the
  symlink on failure. Actions verifies again from outside the server. An external
  check failure after a successful server check flags the job; it does not make an
  additional automatic rollback that might race a subsequent deployment.

## One-time server setup (administrator)

Outside the webroot, install `receiver.php` in a mode-0700 directory and put
`config.json` beside it with these absolute paths:

```json
{
  "live": "/absolute/htdocs/dronemissions",
  "releases": "/absolute/dronemissions-releases",
  "private": "/absolute/dronemissions-private",
  "url": "https://service.studiobaff.com/dronemissions/",
  "node": "/usr/local/bin/node"
}
```

Create releases with mode 0711 (web server must traverse it); never put releases
inside the private application directory. Receiver config mode 0600. PHP CLI must
have PDO SQLite, ZipArchive and `proc_open`; node is required for server JS checks.
The existing PHP private path/environment must remain unchanged.

Create a dedicated unencrypted Ed25519 automation key. Add only its public key to
`authorized_keys`, preserving all existing keys:

```text
restrict,command="/usr/local/bin/php /absolute/deploy-control/receiver.php" ssh-ed25519 … dronemissions-github-deploy
```

The identity has deployment authority for this application. Because deployed PHP
runs as the hosting account, this is not OS-level isolation from that account's
other resources. The forced command prevents interactive SSH, forwarding and
arbitrary original shell commands. Revoke by removing exactly this public key.
The receiver cannot update itself through an application ZIP.

On the first real deployment, the existing live directory is preserved as a
`pre-actions-*` release and converted to a symlink. There is a short rename/link
window on this one-time conversion; subsequent switches are atomic. Test that the
web host permits symlinks before enabling. No release or backup is auto-deleted.

## GitHub setup

Repository Settings → Secrets and variables → Actions:

* `DRONEMISSIONS_DEPLOY_KEY`: **new dedicated private key**, never personal SSH key.
* `DRONEMISSIONS_KNOWN_HOSTS`: host-key entry copied from the already verified local
  known_hosts file. Never trust an unverified `ssh-keyscan` inside the workflow.
* Repository variable `DEPLOY_ENABLED`: initially `false`, then `true` after both
  PRs are merged and production baseline is confirmed.

Environment `production` is recorded by Actions. Restrict its deployment branches
to main; optionally require a reviewer. Branch protection for main should require
review and the `check` job. These repository policies are not changed by this PR.

Use `deploy/configure-github.sh KEY_FILE KNOWN_HOSTS_FILE` from an authenticated
GitHub CLI to save secrets without printing them. It leaves deployment disabled.
No secrets belong in Git, issues, PR comments or chat.

## Rollback

An administrator reads `last-deployment.json` in the releases directory and
switches the live symlink to `previous` using a temporary sibling symlink + rename.
Verify HTTPS afterwards. Do not copy an old SQLite snapshot back over an active
application: it would discard writes since the snapshot. Code rollback does not
undo migrations. Keep migrations backward compatible; destructive changes need a
separate reviewed migration/recovery plan.

## Message for Claude

Please continue the UI/Bridge work on your branch. This deployment PR changes only
`.github/workflows/` and `deploy/`, so it does not overwrite your app or styling.
After both PRs have merged into main and the deployment secrets/variable are set,
finished main commits publish the web public directory automatically. Do not copy
local worktrees or private data into the release. The Mac Bridge remains a separate
local build and is not installed by the web workflow. Add new public asset extensions
to both release allowlists if needed; never add config.json or source project files.
