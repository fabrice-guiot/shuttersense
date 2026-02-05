#!/bin/bash
#
# ShutterSense Database Backup Script
# Creates compressed PostgreSQL backups with tiered retention policy
#
# Usage: ./backup-db.sh
#
# This script is deployed to /opt/shuttersense/scripts/ and scheduled via cron.
# See docs/deployment-hostinger-kvm2.md section 15.2 for cron configuration.
#
# Retention Policy:
#   - Daily backups: kept for 7 days
#   - Weekly backups (Saturday): kept for ~30 days
#   - Monthly backups (first Saturday of month): kept for 1 year
#
# Environment Variables (optional):
#   BACKUP_DIR - Directory to store backups (default: /opt/shuttersense/backups)
#
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/opt/shuttersense/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/shuttersense_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

# Create backup
sudo -u postgres pg_dump shuttersense | gzip > "$BACKUP_FILE"

# Set permissions
chmod 600 "$BACKUP_FILE"
chown shuttersense:shuttersense "$BACKUP_FILE"

echo "Backup created: $BACKUP_FILE"

# =============================================================================
# Tiered Retention Cleanup
# =============================================================================
# - Non-Saturday: delete backup from exactly 7 days ago
# - Saturday: delete old Saturday backups (>30 days) unless first Saturday of
#   their month, and delete any backup older than 1 year
# =============================================================================

cleanup_backups() {
    local today_dow
    today_dow=$(date +%u)  # 1=Monday, 6=Saturday, 7=Sunday

    if [[ "$today_dow" -eq 6 ]]; then
        # Today is Saturday - perform weekly/monthly/yearly cleanup
        echo "Saturday cleanup: checking weekly and monthly retention..."

        for backup in "$BACKUP_DIR"/shuttersense_*.sql.gz; do
            [[ -e "$backup" ]] || continue

            # Extract date from filename (shuttersense_YYYYMMDD_HHMMSS.sql.gz)
            local filename
            filename=$(basename "$backup")
            local date_part=${filename#shuttersense_}
            date_part=${date_part%%_*}  # Get YYYYMMDD

            # Validate date format
            if [[ ! "$date_part" =~ ^[0-9]{8}$ ]]; then
                echo "Skipping invalid filename: $backup"
                continue
            fi

            local year=${date_part:0:4}
            local month=${date_part:4:2}
            local day=${date_part:6:2}

            # Calculate age in days (GNU date syntax for Linux)
            local backup_epoch today_epoch age_days
            backup_epoch=$(date -d "$year-$month-$day" +%s 2>/dev/null) || continue
            today_epoch=$(date +%s)
            age_days=$(( (today_epoch - backup_epoch) / 86400 ))

            # Rule 1: Delete any backup older than 365 days
            if [[ $age_days -gt 365 ]]; then
                rm -f "$backup"
                echo "Deleted (>1 year old): $filename"
                continue
            fi

            # Rule 2: Delete Saturday backups older than 30 days unless first Saturday of month
            local backup_dow
            backup_dow=$(date -d "$year-$month-$day" +%u 2>/dev/null) || continue

            if [[ "$backup_dow" -eq 6 ]] && [[ $age_days -gt 30 ]]; then
                # It's a Saturday backup older than 30 days
                # First Saturday of month has day number 1-7
                local day_num=$((10#$day))  # Force base-10 to handle leading zeros
                if [[ $day_num -gt 7 ]]; then
                    rm -f "$backup"
                    echo "Deleted (Saturday >30 days, not first of month): $filename"
                fi
            fi
        done
    else
        # Not Saturday - delete backup from exactly 7 days ago
        local target_date
        target_date=$(date -d "7 days ago" +%Y%m%d)

        for backup in "$BACKUP_DIR"/shuttersense_${target_date}_*.sql.gz; do
            [[ -e "$backup" ]] || continue
            local filename
            filename=$(basename "$backup")
            rm -f "$backup"
            echo "Deleted (7 days old): $filename"
        done
    fi
}

cleanup_backups
