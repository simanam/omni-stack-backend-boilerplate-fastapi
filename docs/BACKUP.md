# Backup & Recovery Guide

This guide covers backup strategies, procedures, and disaster recovery for OmniStack Backend.

## Table of Contents

1. [Backup Strategy Overview](#backup-strategy-overview)
2. [Database Backups](#database-backups)
3. [File Storage Backups](#file-storage-backups)
4. [Configuration Backups](#configuration-backups)
5. [Backup Verification](#backup-verification)
6. [Recovery Procedures](#recovery-procedures)
7. [Disaster Recovery Plan](#disaster-recovery-plan)

---

## Backup Strategy Overview

### Backup Types

| Type | Frequency | Retention | Purpose |
|------|-----------|-----------|---------|
| Full Database | Daily | 30 days | Complete recovery |
| Incremental | Hourly | 7 days | Point-in-time recovery |
| Transaction Logs | Continuous | 7 days | Minimal data loss |
| File Storage | Daily | 30 days | User uploads recovery |
| Configuration | On change | Indefinite | Infrastructure recovery |

### RPO and RTO Targets

| Metric | Target | Description |
|--------|--------|-------------|
| RPO (Recovery Point Objective) | < 1 hour | Maximum data loss acceptable |
| RTO (Recovery Time Objective) | < 4 hours | Maximum downtime acceptable |

---

## Database Backups

### PostgreSQL Backup Methods

#### 1. Managed Database Backups (Recommended)

Most cloud providers offer automated backups:

**Railway**
- Automatic daily backups
- Point-in-time recovery (PITR)
- 7-day retention by default

**Render**
- Automatic daily backups
- Manual backup creation
- One-click restore

**Supabase**
- Automatic daily backups
- Point-in-time recovery
- Project-level backups

**Neon**
- Automatic branching for backups
- Instant recovery
- 7-day history

#### 2. Manual Backups with pg_dump

```bash
#!/bin/bash
# scripts/backup_database.sh

# Configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-omnistack}"
DB_USER="${DB_USER:-postgres}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/db_backup_${TIMESTAMP}.sql.gz"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create backup
echo "Creating backup: $BACKUP_FILE"
PGPASSWORD="$DB_PASSWORD" pg_dump \
  -h "$DB_HOST" \
  -p "$DB_PORT" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  --format=custom \
  --compress=9 \
  --file="$BACKUP_FILE"

# Verify backup
if [ $? -eq 0 ]; then
  echo "Backup completed successfully"
  ls -lh "$BACKUP_FILE"
else
  echo "Backup failed!"
  exit 1
fi

# Cleanup old backups (keep last 30 days)
find "$BACKUP_DIR" -name "db_backup_*.sql.gz" -mtime +30 -delete
```

#### 3. Continuous Archiving (WAL)

For point-in-time recovery:

```bash
# postgresql.conf settings
archive_mode = on
archive_command = 'cp %p /backup/wal/%f'
archive_timeout = 300  # Archive every 5 minutes
```

### Database Backup to S3

```bash
#!/bin/bash
# scripts/backup_to_s3.sh

BACKUP_FILE=$(ls -t ./backups/db_backup_*.sql.gz | head -1)
S3_BUCKET="s3://your-backup-bucket/database"
TIMESTAMP=$(date +%Y%m%d)

# Upload to S3
aws s3 cp "$BACKUP_FILE" "${S3_BUCKET}/${TIMESTAMP}/" \
  --storage-class STANDARD_IA

# Cleanup local backups older than 7 days
find ./backups -name "db_backup_*.sql.gz" -mtime +7 -delete

echo "Backup uploaded to S3: ${S3_BUCKET}/${TIMESTAMP}/"
```

### Automated Backup Schedule

Add to your crontab:

```bash
# Daily full backup at 2 AM
0 2 * * * /app/scripts/backup_database.sh >> /var/log/backup.log 2>&1

# Upload to S3 at 3 AM
0 3 * * * /app/scripts/backup_to_s3.sh >> /var/log/backup.log 2>&1
```

---

## File Storage Backups

### S3/R2 Cross-Region Replication

For S3-compatible storage, enable cross-region replication:

```bash
# AWS CLI - Enable replication
aws s3api put-bucket-replication \
  --bucket source-bucket \
  --replication-configuration '{
    "Role": "arn:aws:iam::account-id:role/replication-role",
    "Rules": [{
      "Status": "Enabled",
      "Priority": 1,
      "Filter": {},
      "Destination": {
        "Bucket": "arn:aws:s3:::backup-bucket"
      }
    }]
  }'
```

### Manual File Sync

```bash
#!/bin/bash
# scripts/backup_files.sh

SOURCE_BUCKET="s3://your-bucket"
BACKUP_BUCKET="s3://your-backup-bucket"

# Sync files
aws s3 sync "$SOURCE_BUCKET" "$BACKUP_BUCKET" \
  --storage-class GLACIER_IR

echo "File backup completed"
```

---

## Configuration Backups

### Environment Variables

**Never store secrets in backups!** Instead, document which secrets are needed:

```yaml
# config/required_secrets.yml
production:
  - SECRET_KEY
  - DATABASE_URL
  - REDIS_URL
  - SENTRY_DSN
  - STRIPE_SECRET_KEY
  - STRIPE_WEBHOOK_SECRET
  - OPENAI_API_KEY

staging:
  - SECRET_KEY
  - DATABASE_URL
  - REDIS_URL
```

### Infrastructure as Code

Keep deployment configs in version control:

- `railway.toml`
- `render.yaml`
- `fly.toml`
- `docker-compose.yml`
- Kubernetes manifests

---

## Backup Verification

### Automated Backup Testing

```python
#!/usr/bin/env python3
"""
scripts/verify_backup.py
Verify database backup integrity.
"""

import subprocess
import sys
import tempfile
from datetime import datetime

def verify_backup(backup_file: str) -> bool:
    """Verify a database backup can be restored."""

    # Create temporary database for testing
    test_db = f"backup_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        # Create test database
        subprocess.run(
            ["createdb", test_db],
            check=True,
            capture_output=True
        )

        # Restore backup
        subprocess.run(
            ["pg_restore", "-d", test_db, backup_file],
            check=True,
            capture_output=True
        )

        # Verify tables exist
        result = subprocess.run(
            ["psql", "-d", test_db, "-c", "\\dt"],
            capture_output=True,
            text=True
        )

        # Check for expected tables
        expected_tables = ["users", "projects", "files", "webhook_events"]
        for table in expected_tables:
            if table not in result.stdout:
                print(f"Missing table: {table}")
                return False

        print(f"Backup verification successful: {backup_file}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Backup verification failed: {e}")
        return False

    finally:
        # Cleanup test database
        subprocess.run(
            ["dropdb", "--if-exists", test_db],
            capture_output=True
        )

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python verify_backup.py <backup_file>")
        sys.exit(1)

    success = verify_backup(sys.argv[1])
    sys.exit(0 if success else 1)
```

### Weekly Backup Test Schedule

```bash
# Add to crontab - Run every Sunday at 4 AM
0 4 * * 0 /app/scripts/verify_backup.py $(ls -t /backups/*.sql.gz | head -1) >> /var/log/backup_verify.log 2>&1
```

---

## Recovery Procedures

### Database Recovery

#### From pg_dump Backup

```bash
#!/bin/bash
# scripts/restore_database.sh

BACKUP_FILE=$1
DB_NAME="${DB_NAME:-omnistack}"

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: restore_database.sh <backup_file>"
  exit 1
fi

# Confirm before proceeding
echo "WARNING: This will overwrite the database '$DB_NAME'"
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
  echo "Aborted"
  exit 1
fi

# Stop application
echo "Stopping application..."
# Add your stop command here (e.g., docker stop api)

# Drop and recreate database
echo "Recreating database..."
dropdb --if-exists "$DB_NAME"
createdb "$DB_NAME"

# Restore from backup
echo "Restoring from backup..."
pg_restore -d "$DB_NAME" "$BACKUP_FILE"

# Run any pending migrations
echo "Running migrations..."
alembic upgrade head

# Restart application
echo "Starting application..."
# Add your start command here

echo "Recovery complete!"
```

#### Point-in-Time Recovery (PITR)

```bash
# Stop PostgreSQL
pg_ctl stop -D /var/lib/postgresql/data

# Create recovery.conf
cat > /var/lib/postgresql/data/recovery.conf << EOF
restore_command = 'cp /backup/wal/%f %p'
recovery_target_time = '2026-01-10 14:00:00'
EOF

# Start PostgreSQL
pg_ctl start -D /var/lib/postgresql/data
```

### Application Recovery

1. **Restore database** from backup
2. **Verify environment variables** are set
3. **Run migrations** if needed
4. **Deploy application** code
5. **Verify health checks** pass
6. **Test critical paths** manually

---

## Disaster Recovery Plan

### Severity Levels

| Level | Description | Response Time |
|-------|-------------|---------------|
| P1 | Complete service outage | < 15 minutes |
| P2 | Major feature unavailable | < 1 hour |
| P3 | Minor feature affected | < 4 hours |
| P4 | Non-critical issue | Next business day |

### Recovery Runbook

#### P1 - Complete Outage

1. **Acknowledge** (0-5 min)
   - Check monitoring alerts
   - Notify on-call team
   - Start incident channel

2. **Diagnose** (5-15 min)
   - Check service health: `curl https://api.example.com/api/v1/public/health`
   - Review logs in Sentry/Datadog
   - Check infrastructure status pages

3. **Mitigate** (15-60 min)
   - Option A: Roll back to previous version
   - Option B: Scale infrastructure
   - Option C: Failover to backup region

4. **Recover** (1-4 hours)
   - If data loss: Restore from backup
   - Run verification tests
   - Gradually restore traffic

5. **Post-Incident** (24-48 hours)
   - Root cause analysis
   - Update runbooks
   - Implement preventive measures

### Contact List

| Role | Contact | Escalation |
|------|---------|------------|
| On-Call Engineer | PagerDuty | First |
| Engineering Lead | Slack/Phone | Second |
| Database Admin | Slack/Phone | For DB issues |
| Infrastructure | Slack/Phone | For cloud issues |

### Communication Templates

**Status Page Update:**
```
[INVESTIGATING] We are currently investigating issues with [service].
Users may experience [symptoms]. We will provide updates every 30 minutes.
```

**Resolution:**
```
[RESOLVED] The issue with [service] has been resolved. The root cause
was [brief description]. All services are now operating normally.
```

---

## Backup Checklist

### Daily

- [ ] Verify automated backups completed
- [ ] Check backup storage usage
- [ ] Review backup error logs

### Weekly

- [ ] Test backup restoration
- [ ] Verify cross-region replication
- [ ] Review backup retention

### Monthly

- [ ] Full disaster recovery drill
- [ ] Update backup documentation
- [ ] Review and rotate access credentials

### Quarterly

- [ ] Test complete recovery procedure
- [ ] Review RPO/RTO targets
- [ ] Update disaster recovery plan

---

## Monitoring Backup Health

### Alerts to Configure

```yaml
alerts:
  - name: backup_failed
    condition: backup_job_status != "success"
    severity: high

  - name: backup_too_old
    condition: hours_since_last_backup > 24
    severity: high

  - name: backup_storage_low
    condition: backup_storage_available_gb < 10
    severity: medium
```

### Backup Metrics to Track

- Time since last successful backup
- Backup size over time
- Backup duration
- Restore test success rate
- Storage utilization

---

*Last Updated: January 2026*
