# Publishing NodeNix to GitHub

Recommended repository name: **NodeNix**. Description:

> Local Windows diagnostics and IT support toolkit with guided triage, offline reports, privacy profiles and confirmed repairs.

Suggested topics: `powershell`, `python`, `windows`, `it-support`, `helpdesk`, `diagnostics`, `endpoint-security`.

## Choose the account

Use the public GitHub account you want recruiters to see. Before the first commit, set the repository's author name and the **exact GitHub noreply address shown in that account's Settings → Emails**. Do not copy your private email into public commits.

If GitHub is connected to ChatGPT, repository creation/upload can use that connection after the destination account is resolved. A connection suggestion alone does not publish anything.

## Push with Git

Create an empty repository at https://github.com/new. Do not initialize a separate README, license or .gitignore: these are already included in NodeNix.

In PowerShell from the extracted NodeNix folder, with Git installed:

```powershell
git init -b main
git config user.name "sysn1xlabs"
git config user.email "YOUR_EXACT_GITHUB_NOREPLY_ADDRESS"
py -3 scripts/check_public_tree.py
git add .
git diff --cached --stat
git commit -m "Release NodeNix v0.1.2"
git remote add origin https://github.com/sysn1xlabs/NodeNix.git
git push -u origin main
```

Replace the clearly labeled values with your own account details. GitHub requires authentication; use Git Credential Manager or GitHub CLI locally. Do not paste tokens into chat or commit them. A prepared local repository may already have been initialized, in which case `git init` is harmless; do not add a duplicate origin if one already exists.

GitHub upload needs actual source files, including `.github`, `.gitignore` and docs. Uploading only the ZIP puts an archive in the repository rather than creating the source tree and enabling its CI. Git preserves all of these paths.

## Validate the public repository

The `NodeNix validation` workflow is configured for pushes and pull requests. Inspect its actual result in Actions; a checked-in workflow is not a passing run. Windows failures should be fixed before treating native validation as complete.

Only fictional sample reports belong in the repository. The public-source guard rejects live scans and known runtime outputs; inspect staged files and screenshots for information it cannot detect.

## Release assets

Build a clean source ZIP and checksum:

```powershell
py -3 scripts/package_release.py
```

The command prints both paths, normally under `%TEMP%\NodeNix\releases`. It uses an explicit source selection and excludes `.git`, caches and runtime outputs. Verify that `samples/DemoScan.json` is demo data. Use [Release-0.1.2.md](Release-0.1.2.md) as the release description and attach the ZIP plus checksum to tag `v0.1.2`.

The ZIP checksum identifies the downloaded bytes; it is not a signed provenance claim.
