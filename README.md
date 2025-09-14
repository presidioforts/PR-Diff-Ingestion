# Prompt: Implement **P1 — Diff Ingestion** (Code-only, Clone-first)

## GOAL (what to build)

Build a small CLI tool that takes a **repo URL** and **two commit SHAs**, clones the repo to a temp workspace, computes a **deterministic, capped, per-file unified diff**, and outputs a **stable JSON** document with per-file entries, hunks, and flags. **Do not** use commit messages. Code-only.

* Defaults (must be configurable by flags):

  * **rename detection:** ON at **90%**
  * **context lines per hunk:** **3**
  * **per-file cap:** **64 KB** of patch text
  * **total cap:** **800 KB** of combined patch text
* Determinism: same inputs/settings ⇒ **byte-identical JSON** (sorted keys, stable ordering).
* Safety: binaries/LFS/submodules = **metadata only** (no raw blobs).
* Special files: lockfiles/giant generated artifacts → **summarize when capped** (set flags, no big body).
* No CI, no commit messages, no AST parsing.

## PLAN (architecture & scope)

* Language: **Python 3.11** (CLI via argparse), tests via **pytest**.
* Use the **git CLI** via subprocess (no heavy deps).
* Separate modules:

  1. `vcs.py` — clone, ensure SHAs, list changes, build unified patches (text vs binary vs submodule).
  2. `diffpack.py` — build file entries, split hunks, detect EOL-only change, summarize lockfiles, rename flags.
  3. `caps.py` — enforce per-file + global caps; ensure **first & last hunk kept** when truncating.
  4. `serialize.py` — stable sort, stable JSON encoding (sorted keys), UTF-8 with replacement, checksum.
  5. `policies.py` — helpers: identify lockfiles/generated (`package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `*.min.js`, `*.map`, big JSON), submodules.
  6. `main.py` — wire CLI, orchestrate flow, print JSON to stdout or `--json` path.
* Tests:

  * **Unit** tests for capping, hunk splitting, EOL-only detection, rename flag handling.
  * **Property/determinism** test: same inputs → identical bytes/checksum.
  * **Local synthetic repo** fixture (no network) to cover A/M/D/R, binary, submodule, lockfile cases.
  * **Optional integration** test (skipped by default) that runs against the real repo+SHAs you provide.

## EXECUTION STEPS (what to implement, in order)

1. **Scaffold CLI & config**

   * CLI: `p1diff --repo <url> --good <sha> --cand <sha> [--branch <name>] [--cap-total 800000] [--cap-file 64000] [--context 3] [--find-renames 90] [--json out.json]`
   * Validate args; normalize numbers; build a config object.

2. **Clone workspace**

   * Create temp dir; clone minimal.
   * Fetch `commit_good` and `commit_candidate`.
   * Verify both SHAs exist; if not, exit with JSON error (`COMMIT_NOT_FOUND`).
   * Never require a working checkout; operate on objects.

3. **Discover change set**

   * Compute file changes between the two SHAs with **rename detection @ 90%**.
   * Build metadata per file: `status (A/M/D/R/C/T)`, `path_old`, `path_new`, `rename_score?`, `mode_old/new`, `size_old/new`, `is_binary`, `is_submodule`.
   * Stable order: by `path_new` (or `path_old` if deleted), then by `status`.

4. **Generate unified patches (text files only)**

   * Build unified diff with **context = 3** lines (configurable).
   * Split into hunks with fields:
     `old_start`, `old_lines`, `new_start`, `new_lines`, `header`, `added`, `deleted`, `patch (text)`
   * Detect **EOL-only** change (set `eol_only_change:true`).
   * **Binary/LFS/Submodule**: **no** hunk body; include minimal metadata and, for submodule, old/new submodule SHAs.

5. **Apply caps & special policies**

   * **Per-file cap (64 KB)**: append hunks until cap; on overflow set `truncated:true` and **ensure first & last hunk** are preserved; record `omitted_hunks_count`.
   * **Global cap (800 KB)**: if adding a file would exceed cap, **do not** include its hunks; increment `omitted_files_count`; keep metadata-only entry.
   * **Lockfiles/generated**: if patch > per-file cap, set `summarized:true` and omit patch text (cheap count summary optional), no large bodies.

6. **Serialize deterministically**

   * Build output with:
     `provenance { repo_url, commit_good, commit_candidate, branch_name?, caps { … }, rename_detection { enabled:true, threshold_pct:90 } }`
     `files[]` entries as above; `omitted_files_count`; `notes[]`.
   * **Stable sort** files/hunks; encode to JSON with **sorted keys** and UTF-8 with replacement; compute **SHA-256 checksum** of the JSON bytes and place it at `provenance.checksum`.

7. **Error handling (JSON)**

   * Return machine-readable errors with codes: `CLONE_FAILED`, `COMMIT_NOT_FOUND`, `CAPS_INVALID`.
   * Do **not** crash on oversize—emit truncation flags and counts.

8. **Unit tests** (pytest)

   * Fixtures that create tiny throwaway repos to simulate:

     * A/M/D changes; **rename** (R) with threshold; **binary** file; **submodule** (gitlink) entry; **EOL-only** change; **lockfile** that exceeds cap; **global cap** overflow.
   * Determinism test: run twice with same inputs, compare JSON bytes checksum.
   * Per-file cap test: ensure first & last hunk are present when truncated.
   * JSON schema sanity (keys present, types plausible).

9. **Optional integration test** (skipped by default)

   * Use (skip if offline):

     * `repo_url`: `https://github.com/presidioforts/direct-finetune-rag-model.git`
     * `commit_good`: `ba7765dd48c0ba51f4fd12cde48fd100aecdb743`
     * `commit_candidate`: `d7a39abec5a282b9955afdd1649a5f1bafae35f7`
     * `branch_name`: `codex/move-prompts-to-external-template-files`
   * Validate output shape and that `checksum` is stable across two runs.

10. **README**

* Show CLI usage, example output snippet, and the definition of done.
* Document caps, rename threshold, and flags.

## OUTPUT JSON SHAPE (contract to implement)

```json
{
  "provenance": {
    "repo_url": "<string>",
    "commit_good": "<sha>",
    "commit_candidate": "<sha>",
    "branch_name": "<string|optional>",
    "caps": {"total_bytes": 800000, "per_file_bytes": 64000, "context_lines": 3},
    "rename_detection": {"enabled": true, "threshold_pct": 90},
    "checksum": "<sha256>"
  },
  "files": [
    {
      "status": "A|M|D|R|C|T",
      "path_old": "<string|null>",
      "path_new": "<string|null>",
      "rename_score": "<int|null>",
      "mode_old": "<string|null>",
      "mode_new": "<string|null>",
      "size_old": "<int|null>",
      "size_new": "<int|null>",
      "is_binary": "<bool>",
      "is_submodule": "<bool|default:false>",
      "eol_only_change": "<bool|default:false>",
      "summarized": "<bool|default:false>",
      "truncated": "<bool|default:false>",
      "omitted_hunks_count": "<int|optional>",
      "submodule": {"old_sha":"<sha>","new_sha":"<sha>"},
      "hunks": [
        {
          "header": "@@ -<old_start>,<old_lines> +<new_start>,<new_lines> @@",
          "old_start": "<int>", "old_lines": "<int>",
          "new_start": "<int>", "new_lines": "<int>",
          "added": "<int>", "deleted": "<int>",
          "patch": "<string>"
        }
      ]
    }
  ],
  "omitted_files_count": "<int>",
  "notes": ["<string>", "..."]
}
```

## ACCEPTANCE CHECKLIST (must all pass)

* Caps enforced; truncations and omissions flagged; never exceed limits.
* Renames show as `R` with `path_old`, `path_new`, `rename_score`.
* Binaries and submodules have **no** hunk bodies.
* EOL-only changes flagged.
* Deterministic: identical JSON bytes (and `checksum`) for identical inputs/settings.
* Clear JSON errors for clone/commit/caps issues.

---

**Now generate the full implementation (code + tests + README) following the plan above.**
