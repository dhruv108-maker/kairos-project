#!/bin/bash

set -Eeuo pipefail
umask 077

# AWS RDS configuration
DB_HOST="sagiros-db.cyxoemmc2q2b.us-east-1.rds.amazonaws.com"
DB_PORT="3306"
DB_USER="admin"
DB_NAME="kairos"

# Secure password prompt
read -rsp "Enter MySQL password: " DB_PASSWORD
echo
export MYSQL_PWD="$DB_PASSWORD"
unset DB_PASSWORD
trap 'unset MYSQL_PWD' EXIT

# Output directory
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_DIR="./kairos_db_export_${TIMESTAMP}"
mkdir -p "$OUTPUT_DIR"

# TCP connection settings
MYSQL_ARGS=(
  --protocol=TCP
  --host="$DB_HOST"
  --port="$DB_PORT"
  --user="$DB_USER"
  --connect-timeout=15
)

echo "Checking AWS RDS connection..."

mysql "${MYSQL_ARGS[@]}" 
  --batch 
  --skip-column-names 
  "$DB_NAME" 
  -e "SELECT VERSION(), DATABASE();"

# Check mysqldump availability and version
echo
echo "Checking mysqldump client..."
mysqldump --version

# Common dump arguments
DUMP_ARGS=(
  --protocol=TCP
  --host="$DB_HOST"
  --port="$DB_PORT"
  --user="$DB_USER"
  --single-transaction
  --skip-lock-tables
)

# Export schema
echo
echo "Exporting schema..."

mysqldump "${DUMP_ARGS[@]}" 
  --no-data 
  "$DB_NAME" \
  > "$OUTPUT_DIR/kairos_schema.sql"

# Export complete database
echo "Exporting complete database..."

mysqldump "${DUMP_ARGS[@]}" 
  "$DB_NAME" \
  > "$OUTPUT_DIR/kairos_full_backup.sql"

# Validate generated files
if [[ ! -s "$OUTPUT_DIR/kairos_schema.sql" ]]; then
  echo "ERROR: Schema file is empty."
  exit 1
fi

if [[ ! -s "$OUTPUT_DIR/kairos_full_backup.sql" ]]; then
  echo "ERROR: Full backup file is empty."
  exit 1
fi

echo
echo "SUCCESS: Database exports completed."
echo "Schema: $OUTPUT_DIR/kairos_schema.sql"
echo "Full backup: $OUTPUT_DIR/kairos_full_backup.sql"
echo
ls -lh "$OUTPUT_DIR"