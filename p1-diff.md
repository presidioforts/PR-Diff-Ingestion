# P1 — Diff Ingestion (Code-Only) — MVP Specification v1.0

## 1) Overview

Produce a **small, deterministic JSON** describing exactly what changed between two commits of a Git repository. The tool **clones** the repo to a temp workspace, computes a **per-file unified diff** (with strict byte caps), and emits a stable payload for downstream analysis.
**No CI, no commit messages, no AST parsing.**

---

## 2) Scope

**In:** clone → diff (with rename detection) → hunk splitting → caps → deterministic JSON.
**Out (v1):** submodule recursion; executing builds/tests; LLM reasoning; PR APIs.

---

## 3) Interfaces

### CLI

```
p1diff --repo <url> --good <sha> --cand <sha>
       [--branch <name>]
       [--cap-total 800000] [--cap-file 64000] [--context 3]
       [--find-renames 90]
       [--json out.json]
       [--keep-workdir] [--keep-on-error]
```

### Exit & Envelope

* Exit code: **0** success; **non-zero** error.
* Always print JSON envelope:

  * Success: `{"ok": true, "data": <payload>}`
  * Error: `{"ok": false, "error": {"code":"…","message":"…","details":{…}}}`

---

## 4) Inputs & Config

* **Required:** `repo_url`, `commit_good`, `commit_candidate`
* **Optional:** `branch_name` (label/fetch hint only)
* **Caps (UTF-8 bytes):** `cap_total` (default **800 000**), `cap_file` (default **64 000**), `context_lines` (default **3**)
* **Rename detection:** enabled (default) with threshold **90%**
* **Policies:** lockfile/generated detection; binary/submodule handling
* **Workspace:** ephemeral temp dir by default; `--keep-*` flags for debugging
* **Git requirement:** **git ≥ 2.30** (validated)

---

## 5) Output (payload inside `data`)

### Provenance

* `repo_url`, `commit_good`, `commit_candidate`, `branch_name`
* `caps` `{total_bytes, per_file_bytes, context_lines}`
* `rename_detection` `{enabled, threshold_pct}`
* `git_version`, `diff_algorithm` (e.g., `"myers"`)
* `env_locks` (e.g., `LC_ALL=C`, color off, `core.autocrlf=false`)
* `checksum` (SHA-256 of serialized payload)

### Files Array (per changed entry)

* `status`: `A|M|D|R|C|T`
* `path_old`, `path_new`
* `rename_score` (if R/C), `rename_tiebreaker` (`path|size|lex`, when applicable)
* `mode_old`, `mode_new`
* `size_old`, `size_new`
* `is_binary` (bool), `is_submodule` (bool)
* `eol_only_change` (bool), `whitespace_only_change` (bool)
* `summarized` (bool; for oversized lockfiles/generated), `truncated` (bool)
* `omitted_hunks_count` (int, optional)
* `submodule` `{old_sha, new_sha}` (if gitlink)
* `hunks[]` (text files only):

  * `header` `"@@ -<old_start>,<old_lines> +<new_start>,<new_lines> @@"`
  * `old_start`, `old_lines`, `new_start`, `new_lines`
  * `added`, `deleted`
  * `patch` (bounded text)

### Totals

* `omitted_files_count` (int)
* `notes[]` (e.g., “lockfiles summarized”, “CRLF→LF in 2 files”)

---

## 6) Processing Pipeline

1. **Workspace**
   Create temp dir; record config in provenance. Signal/exception-safe cleanup.
   Flags: `--keep-workdir`, `--keep-on-error`.

2. **Clone & Verify**
   Clone minimally; fetch SHAs directly (use `branch_name` as a hint only).
   Validate `git_version ≥ 2.30`; ensure both SHAs exist.
   Errors: `CLONE_FAILED`, `COMMIT_NOT_FOUND`, `GIT_VERSION_UNSUPPORTED`.

3. **Change Discovery**
   Compute `commit_good…commit_candidate` with rename detection (90%).
   Build file metadata: status, paths, modes, sizes, binary/submodule flags.
   **Rename ties (deterministic):** path similarity → smallest size delta → lexicographic old path; expose `rename_tiebreaker`.

4. **Patch Generation (text files)**
   Unified diff with `context_lines` (default 3).
   Detect flags: `eol_only_change`, `whitespace_only_change`.
   **Binary/LFS/Submodule:** metadata-only; no patch bodies. Submodule emits `{old_sha,new_sha}`.

5. **Caps & Policies**
   **Per-file cap (64 KB):** include hunks until cap; if truncating, **keep full context** for first & last included hunks. For middle hunks, you may shrink context to 1 line before dropping. Track `omitted_hunks_count`; set `truncated:true`.
   **Global cap (800 KB):** if adding a file exceeds cap, include **metadata-only**, increment `omitted_files_count`.
   **Lockfiles/generated (default set below):** if oversized, set `summarized:true`, omit big bodies.

6. **Stabilize & Serialize**
   Stable sort files by effective new path (fallback old), then status; hunks by position.
   UTF-8 with replacement; stable JSON key order.
   Compute `checksum` (SHA-256) over the payload.

---

## 7) Policies (defaults)

**Lockfiles/Generated (configurable baseline):**

* JS: `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `npm-shrinkwrap.json`
* Python: `poetry.lock`, `Pipfile.lock`
* Java: `gradle.lockfile`
* Ruby: `Gemfile.lock`
* PHP: `composer.lock`
* Rust: `Cargo.lock`
* Go: `go.sum`
* Swift: `Package.resolved`
* Elixir: `mix.lock`
* .NET: `packages.lock.json`
* Minified/maps: `*.min.js`, `*.map` (large)
  **Behavior:** If patch > per-file cap ⇒ `summarized:true` (no large diff text).

**Binary detection:** use Git’s built-in; `is_binary:true`, metadata only.
**Submodules:** report only `{old_sha,new_sha}`; no recursion (v1).
**Whitespace/EOL:** set booleans when applicable.

---

## 8) Errors (JSON)

* `GIT_VERSION_UNSUPPORTED` (include detected version)
* `CLONE_FAILED`
* `COMMIT_NOT_FOUND`
* `CAPS_INVALID`
* `NETWORK_TIMEOUT` (clone/fetch exceeded timeout)
* All errors return `{"ok": false, "error": {...}}` and non-zero exit.

---

## 9) Non-Functional / Ops

* **Determinism:** Same inputs/settings ⇒ byte-identical JSON (checksum match).
* **Performance target:** Medium diffs complete in < 2–5 s on a dev laptop.
* **Timeouts/Retry:** Reasonable network timeout with one retry; then `NETWORK_TIMEOUT`.
* **Security/Privacy:** No blobs for binaries; no secret scraping; ephemeral workspace by default.

---

## 10) Acceptance Criteria (Definition of Done)

* Caps enforced; truncation/omission flags present; never exceed limits.
* Renames detected; ties resolved deterministically; `rename_score` and `rename_tiebreaker` included.
* Binary/LFS/Submodule entries have **no** patch text.
* EOL/whitespace-only changes flagged where applicable.
* Deterministic output: two runs with same inputs/settings produce identical bytes (checksum equal).
* Clear JSON errors with non-zero exits on failures.

---

## 11) Test Plan (minimum)

* **Determinism:** run twice → identical JSON & checksum.
* **Caps:** per-file truncation (first/last kept), global cap overflow (`omitted_files_count > 0`).
* **Statuses:** A/M/D/R/C/T coverage; rename tie-break behavior.
* **Specials:** binary file; submodule (gitlink) entry; lockfile > cap; EOL-only & whitespace-only deltas.
* **Negative:** bad repo URL; missing SHAs; old git version; network timeout.

---

## 12) Defaults (v1)

* `cap_total`: **800 000** bytes
* `cap_file`: **64 000** bytes
* `context_lines`: **3**
* `rename_detection.threshold_pct`: **90**
* `diff_algorithm`: **myers**
* Workspace: ephemeral (override via `--keep-workdir`, `--keep-on-error`)

---

## 13) Example Inputs (for manual test)

* `repo_url`: `https://github.com/presidioforts/direct-finetune-rag-model.git`
* `commit_good`: `ba7765dd48c0ba51f4fd12cde48fd100aecdb743`
* `commit_candidate`: `d7a39abec5a282b9955afdd1649a5f1bafae35f7`
* `branch_name`: `codex/move-prompts-to-external-template-files`

*(No execution implied—reference only.)*

---

**This spec is the single source of truth for P1.**
