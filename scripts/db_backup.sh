#!/bin/bash
set -e

# Configuration
DB_CONTAINER_NAME=${1:-learnova-db-1}
DB_USER=${POSTGRES_USER:-postgres}
DB_NAME=${POSTGRES_DB:-learnova}
BACKUP_DIR=${BACKUP_DIR:-./backups}
RETENTION_DAYS=${RETENTION_DAYS:-7}

# Timestamp for the backup file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_backup_${TIMESTAMP}.sql.gz"

echo "Starting PostgreSQL backup for ${DB_NAME} on container ${DB_CONTAINER_NAME}..."

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

# Execute pg_dump within the docker container and gzip the output
docker exec -t ${DB_CONTAINER_NAME} pg_dump -U ${DB_USER} -d ${DB_NAME} -c -O | gzip > "${BACKUP_FILE}"

if [ $? -eq 0 ]; then
  echo "Backup successfully created at ${BACKUP_FILE}"
else
  echo "Backup failed!" >&2
  exit 1
fi

# Apply retention policy
echo "Cleaning up backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "${DB_NAME}_backup_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -exec rm -f {} \;

echo "Backup process complete."
