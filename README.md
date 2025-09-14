# PR-Diff-Ingestion
Build a small CLI tool that takes a repo URL and two commit SHAs, clones the repo to a temp workspace, computes a deterministic, capped, per-file unified diff, and outputs a stable JSON document with per-file entries, hunks, and flags. Do not use commit messages. Code-only.
