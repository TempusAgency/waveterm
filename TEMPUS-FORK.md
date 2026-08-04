# TEMPUS-FORK

This repository is a fork of [wavetermdev/waveterm](https://github.com/wavetermdev/waveterm), maintained by
TempusAgency. Upstream code, upstream conventions — plus a small, deliberately reviewable set of local changes.

|            |                                |
| ---------- | ------------------------------ |
| Fork line  | `tempus/custom`                |
| Base       | upstream tag `v0.14.5`         |
| `origin`   | `TempusAgency/waveterm` (fork) |
| `upstream` | `wavetermdev/waveterm`         |

## How the fork is organized

`tempus/custom` is a linear stack of commits sitting directly on top of an upstream release tag, and **one feature is
one commit**. That is mechanics, not style: the fork is carried forward by replaying those commits onto the next release
tag, so a commit holding two features cannot be rebased with only one feature's context in mind, cannot be reverted to
switch a single customization off, and cannot be offered upstream on its own.

Everything the fork owns is therefore one command away:

```bash
git log --oneline v0.14.5..tempus/custom     # the feature list
git diff v0.14.5..tempus/custom              # every line the fork owns
```

Because of that, the fork adds no in-code provenance markers.

## Updating to a new upstream release

Automatic updates are disabled on purpose (commit `chore(build): pin the Tempus fork off the upstream update channel`):
an update resolved from the upstream feed would install the official build over this fork and silently remove every
fork-only change. Both layers are pinned — `publish` is `null` in `electron-builder.config.cjs`, so the packaged app
carries no update manifest at all, and `autoupdate:enabled` defaults to `false` in
`pkg/wconfig/defaultconfig/settings.json`.

The consequence is that updating is a deliberate act: the fork is moved onto a newer upstream tag by hand, and the
commits above are replayed onto it.

```bash
git fetch upstream --tags
git rebase --onto <new-tag> v0.14.5 tempus/custom
```

Then update the base tag recorded in the table above. Rebase onto tags, never onto `upstream/main`. The full playbook —
the archive tag taken first, `rerere`, regenerating rather than merging generated files, and the `git range-diff` audit
that proves nothing drifted — is in the governing document.

## Running the fork

Launch the fork with `WAVETERM_DATA_HOME` and `WAVETERM_CONFIG_HOME` pointed somewhere other than the official Wave
directories.

Both builds otherwise resolve the same paths: the Electron side calls `envPaths("waveterm", ...)` and the Go side
hardcodes `appBundle := "waveterm"`, and neither is affected by a changed `appId`. Sharing those directories means
sharing one `settings.json` and one database — and database migrations run when the app opens, so the official build
and the fork can migrate the same file out from under each other.

## Governing document

The rules this fork is held to — the nine commit gates, the placement and naming policy, the seam-risk ladder, the
config-key namespaces, the per-feature designs and the rebase playbook — live outside the repository:

```
/Users/tempus/Documents/TEMPUSIDIAN Vault 1/Claude Vault/WAVE REWORK/Wave custom 0.1/FORK-ARCHITECTURE.md
```

Where that document and any other design note disagree, the governing document wins.

## Seam ledger

Files the fork edits in upstream code, generated from the `Tempus-Seams` commit trailers:

```bash
git log --format='%h %s%n    %(trailers:key=Tempus-Seams,valueonly)' v0.14.5..tempus/custom
```

## Fork-only config keys

None yet. Keys in the `tempus:` namespace are documented here rather than in `docs/docs/config.mdx`, which is published
to `docs.waveterm.dev` and describes upstream Wave.
