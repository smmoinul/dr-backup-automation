# DR Backup Automation & RTO/RPO Tracker

Python-based backup automation with integrity verification (checksums), full/incremental rotation logic, and an RTO/RPO compliance tracker — designed to complement enterprise tools like Veeam by providing a lightweight, scriptable layer for file-level backups and DR-readiness reporting.

## Why this exists

Beyond the enterprise backup platform (Veeam/similar), infra teams often need a scriptable way to back up specific application data/configs, verify integrity after the fact, and prove — with a paper trail — that RTO/RPO targets are actually being met. This project builds that layer: full+incremental rotation, SHA-256 verification, and a CSV-based compliance log that can be handed to an auditor or referenced in a DR runbook.

## Features

- **Full + incremental backup rotation** — configurable schedule (e.g. full backup Sunday, incrementals Mon-Sat), with retention pruning
- **Checksum-verified integrity** — SHA-256 hash generated at backup time and re-verified on a schedule, flags silent corruption
- **RTO/RPO compliance tracking** — logs actual backup completion time vs. configured RPO target, flags any backup that would violate the RPO window if a failure happened right now
- **Restore-test simulation** — a script that restores a backup to a scratch directory and diffs it against the source, so "we tested our backups" is provable, not assumed
- **Email alert on backup failure or verification failure**
- **CSV compliance log** — one row per backup job run, suitable for DR audit evidence

## Project structure

```
dr-backup-automation/
├── backup_job.py           # runs full/incremental backup + checksum
├── verify_integrity.py     # re-checks stored checksums against current files
├── restore_test.py         # restores latest backup to scratch dir & diffs vs source
├── rpo_compliance_report.py# generates RTO/RPO compliance CSV from job logs
├── config.example.yaml
├── requirements.txt
└── sample_output/
    ├── backup_job_log_sample.csv
    └── rpo_compliance_report_sample.csv
```

## Setup

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml   # set source/destination paths & RPO target

# Run a backup (auto-detects full vs incremental based on day-of-week schedule)
python backup_job.py --config config.yaml

# Verify integrity of existing backups
python verify_integrity.py --config config.yaml

# Simulate a restore and diff against source (monthly DR test)
python restore_test.py --config config.yaml --backup-date 2026-08-09

# Generate RTO/RPO compliance report
python rpo_compliance_report.py --log backups/job_log.csv --rpo-hours 24
```

## Sample config

```yaml
source_paths:
  - /srv/app-config
  - /srv/db-dumps

destination_root: /mnt/backup-dr

schedule:
  full_backup_day: Sunday
  retention_days: 30

rpo_target_hours: 24

alerting:
  email:
    enabled: true
    smtp_host: smtp.gmail.com
    smtp_port: 587
    from_address: alerts@example.com
    to_address: itsmoinul@gmail.com
    username: "${SMTP_USER}"
    password: "${SMTP_PASSWORD}"
```

## Sample compliance report

| backup_date | type | duration_min | rpo_target_hrs | rpo_met | verified |
|---|---|---|---|---|---|
| 2026-08-09 | incremental | 4.2 | 24 | Yes | Yes |
| 2026-08-08 | incremental | 3.9 | 24 | Yes | Yes |
| 2026-08-03 | full | 38.1 | 24 | Yes | Yes |

## Tech stack

Python 3.10+, hashlib (stdlib), shutil (stdlib), PyYAML

## License

MIT
