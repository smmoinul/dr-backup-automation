#!/usr/bin/env python3
"""
verify_integrity.py
----------------------
Re-hashes every file recorded in a backup's checksums.json manifest and
compares against the stored hash — catches silent corruption (bit rot,
incomplete copies, storage-media faults) that a simple "file exists" check
would miss.

Usage:
    python verify_integrity.py --config config.yaml [--date 2026-08-09]
"""

import argparse
import hashlib
import json
import os
from datetime import datetime

import yaml


def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_backup(dest_dir):
    manifest_path = os.path.join(dest_dir, "checksums.json")
    if not os.path.isfile(manifest_path):
        print(f"No checksum manifest found in {dest_dir}")
        return

    with open(manifest_path) as f:
        manifest = json.load(f)

    ok, missing, corrupted = 0, 0, 0
    for file_path, expected_hash in manifest.items():
        if not os.path.isfile(file_path):
            print(f"[MISSING]   {file_path}")
            missing += 1
            continue
        actual_hash = sha256_of_file(file_path)
        if actual_hash == expected_hash:
            ok += 1
        else:
            print(f"[CORRUPTED] {file_path}")
            corrupted += 1

    print(f"\nVerified {dest_dir}: {ok} OK, {missing} missing, {corrupted} corrupted "
          f"(out of {len(manifest)} files)")
    return {"ok": ok, "missing": missing, "corrupted": corrupted, "total": len(manifest)}


def main():
    parser = argparse.ArgumentParser(description="Verify backup integrity against stored checksums")
    parser.add_argument("--config", required=True, help="Path to config.yaml")
    parser.add_argument("--date", default=None, help="Backup date to verify (YYYY-MM-DD), default: today")
    args = parser.parse_args()

    with open(args.config) as f:
        cfg = yaml.safe_load(f)

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")
    dest_dir = os.path.join(cfg["destination_root"], date_str)

    verify_backup(dest_dir)


if __name__ == "__main__":
    main()
