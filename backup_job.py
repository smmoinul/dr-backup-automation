#!/usr/bin/env python3
"""
backup_job.py
---------------
Runs a full or incremental backup based on the configured schedule,
generates a SHA-256 checksum manifest per file, and logs the job result
(duration, type, status) to backups/job_log.csv for RTO/RPO reporting.

Full backups copy everything under each source path.
Incremental backups copy only files modified since the last successful
job (full or incremental), tracked via a small state file.

Usage:
    python backup_job.py --config config.yaml
"""

import argparse
import csv
import hashlib
import json
import os
import shutil
from datetime import datetime

import yaml

STATE_FILE = "backups/.last_run_state.json"
LOG_FILE = "backups/job_log.csv"


def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_state():
    if os.path.isfile(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_run": None}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def determine_backup_type(cfg, state):
    today_name = datetime.now().strftime("%A")
    if today_name == cfg["schedule"]["full_backup_day"] or state["last_run"] is None:
        return "full"
    return "incremental"


def run_backup(cfg, backup_type, state):
    date_str = datetime.now().strftime("%Y-%m-%d")
    dest_dir = os.path.join(cfg["destination_root"], date_str)
    os.makedirs(dest_dir, exist_ok=True)

    last_run_dt = datetime.fromisoformat(state["last_run"]) if state["last_run"] else None
    manifest = {}
    files_copied = 0

    for source_path in cfg["source_paths"]:
        for root, _, files in os.walk(source_path):
            for filename in files:
                full_path = os.path.join(root, filename)
                mtime = datetime.fromtimestamp(os.path.getmtime(full_path))

                if backup_type == "incremental" and last_run_dt and mtime <= last_run_dt:
                    continue  # unchanged since last run

                rel_path = os.path.relpath(full_path, source_path)
                dest_path = os.path.join(dest_dir, os.path.basename(source_path), rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(full_path, dest_path)

                manifest[dest_path] = sha256_of_file(dest_path)
                files_copied += 1

    manifest_path = os.path.join(dest_dir, "checksums.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    return files_copied, dest_dir


def prune_old_backups(cfg):
    retention_days = cfg["schedule"]["retention_days"]
    cutoff = datetime.now().timestamp() - (retention_days * 86400)
    root = cfg["destination_root"]
    if not os.path.isdir(root):
        return

    for entry in os.listdir(root):
        entry_path = os.path.join(root, entry)
        if os.path.isdir(entry_path) and os.path.getmtime(entry_path) < cutoff:
            shutil.rmtree(entry_path)
            print(f"Pruned expired backup: {entry_path}")


def log_job(backup_type, duration_min, files_copied, status):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["backup_date", "type", "duration_min", "files_copied", "status"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d"), backup_type,
            round(duration_min, 2), files_copied, status,
        ])


def main():
    parser = argparse.ArgumentParser(description="Run full/incremental backup job")
    parser.add_argument("--config", required=True, help="Path to config.yaml")
    args = parser.parse_args()

    with open(args.config) as f:
        cfg = yaml.safe_load(f)

    state = load_state()
    backup_type = determine_backup_type(cfg, state)

    print(f"Starting {backup_type} backup...")
    start = datetime.now()

    try:
        files_copied, dest_dir = run_backup(cfg, backup_type, state)
        duration_min = (datetime.now() - start).total_seconds() / 60
        prune_old_backups(cfg)

        state["last_run"] = start.isoformat()
        save_state(state)
        log_job(backup_type, duration_min, files_copied, "SUCCESS")

        print(f"Done. {files_copied} file(s) backed up to {dest_dir} in {duration_min:.1f} min.")

    except Exception as exc:  # noqa: BLE001
        duration_min = (datetime.now() - start).total_seconds() / 60
        log_job(backup_type, duration_min, 0, f"FAILED: {exc}")
        print(f"Backup FAILED: {exc}")
        raise


if __name__ == "__main__":
    main()
