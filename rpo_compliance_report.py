#!/usr/bin/env python3
"""
rpo_compliance_report.py
---------------------------
Reads backups/job_log.csv (written by backup_job.py) and produces an
RTO/RPO compliance report: for each backup, whether it completed within
the configured RPO window relative to the previous successful backup —
i.e. "if disaster struck right now, would we lose more data than the
RPO target allows?"

Usage:
    python rpo_compliance_report.py --log backups/job_log.csv --rpo-hours 24
"""

import argparse
import csv
from datetime import datetime, timedelta


def main():
    parser = argparse.ArgumentParser(description="Generate RTO/RPO compliance report from backup job log")
    parser.add_argument("--log", required=True, help="Path to job_log.csv")
    parser.add_argument("--rpo-hours", type=float, required=True, help="RPO target in hours")
    parser.add_argument("--out", default="rpo_compliance_report.csv", help="Output CSV path")
    args = parser.parse_args()

    rows = []
    with open(args.log) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    successful_rows = [r for r in rows if r["status"] == "SUCCESS"]
    successful_rows.sort(key=lambda r: r["backup_date"])

    report = []
    prev_date = None
    for row in successful_rows:
        current_date = datetime.strptime(row["backup_date"], "%Y-%m-%d")
        if prev_date:
            gap_hours = (current_date - prev_date).total_seconds() / 3600
        else:
            gap_hours = 0

        rpo_met = gap_hours <= args.rpo_hours

        report.append({
            "backup_date": row["backup_date"],
            "type": row["type"],
            "duration_min": row["duration_min"],
            "gap_since_previous_hrs": round(gap_hours, 1),
            "rpo_target_hrs": args.rpo_hours,
            "rpo_met": "Yes" if rpo_met else "No — GAP EXCEEDED",
        })
        prev_date = current_date

    with open(args.out, "w", newline="") as f:
        fieldnames = ["backup_date", "type", "duration_min", "gap_since_previous_hrs", "rpo_target_hrs", "rpo_met"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report)

    violations = sum(1 for r in report if "GAP EXCEEDED" in r["rpo_met"])
    print(f"Report written to {args.out}")
    print(f"{len(report)} backup(s) analyzed | {violations} RPO violation(s) found")


if __name__ == "__main__":
    main()
