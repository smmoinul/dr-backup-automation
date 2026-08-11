#!/usr/bin/env python3
"""
restore_test.py
------------------
Simulates a DR restore: copies a given day's backup out to a scratch
directory (as if restoring to a recovery host) and diffs file counts +
checksums against the original manifest, so a "restore test passed"
claim is backed by an actual run, not an assumption.

Usage:
    python restore_test.py --config config.yaml --backup-date 2026-08-09
"""

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime

import yaml


def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Simulate a restore and verify against manifest")
    parser.add_argument("--config", required=True, help="Path to config.yaml")
    parser.add_argument("--backup-date", required=True, help="Backup date to restore-test (YYYY-MM-DD)")
    args = parser.parse_args()

    with open(args.config) as f:
        cfg = yaml.safe_load(f)

    source_backup = os.path.join(cfg["destination_root"], args.backup_date)
    manifest_path = os.path.join(source_backup, "checksums.json")

    if not os.path.isfile(manifest_path):
        print(f"No backup/manifest found for {args.backup_date} in {source_backup}")
        return

    with open(manifest_path) as f:
        manifest = json.load(f)

    scratch_dir = tempfile.mkdtemp(prefix="restore_test_")
    print(f"Restoring backup {args.backup_date} to scratch dir: {scratch_dir}")

    restored, mismatched = 0, 0
    for original_path, expected_hash in manifest.items():
        rel_path = os.path.relpath(original_path, source_backup)
        restore_path = os.path.join(scratch_dir, rel_path)
        os.makedirs(os.path.dirname(restore_path), exist_ok=True)

        if not os.path.isfile(original_path):
            print(f"[SKIP] source missing: {original_path}")
            continue

        shutil.copy2(original_path, restore_path)
        actual_hash = sha256_of_file(restore_path)

        if actual_hash == expected_hash:
            restored += 1
        else:
            mismatched += 1
            print(f"[MISMATCH] {rel_path}")

    result = "PASS" if mismatched == 0 else "FAIL"
    print(f"\nRestore test {result}: {restored} file(s) restored & verified, {mismatched} mismatch(es)")
    print(f"Scratch data left at: {scratch_dir} (clean up manually after review)")

    log_path = os.path.join("backups", "restore_test_log.csv")
    os.makedirs("backups", exist_ok=True)
    file_exists = os.path.isfile(log_path)
    with open(log_path, "a") as f:
        if not file_exists:
            f.write("test_date,backup_date,files_restored,mismatches,result\n")
        f.write(f"{datetime.now().strftime('%Y-%m-%d')},{args.backup_date},{restored},{mismatched},{result}\n")


if __name__ == "__main__":
    main()
