#!/bin/bash
set -e

# Configuration
DB_CONTAINER_NAME=${1:-learnova-db-1}
DB_USER=${POSTGRES_USER:-postgres}
DB_NAME=${POSTGRES_DB:-learnova}
BACKUP_FILE=$2

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: ./db_restore.sh <container_name> <path_to_backup_file.sql.gz>"
  exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Error: Backup file $BACKUP_FILE not found!"
  exit 1
fi

echo "WARNING: This will drop and recreate the database '${DB_NAME}' on container '${DB_CONTAINER_NAME}'."
read -p "Are you sure you want to proceed? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Restore cancelled."
    exit 1
fi

echo "Dropping and recreating database ${DB_NAME}..."
# Drop and recreate (Note: active connections will block drop, so might need forced disconnect)
docker exec -it ${DB_CONTAINER_NAME} psql -U ${DB_USER} -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME} WITH (FORCE);"
docker exec -it ${DB_CONTAINER_NAME} psql -U ${DB_USER} -d postgres -c "CREATE DATABASE ${DB_NAME};"

echo "Restoring from $BACKUP_FILE..."
gunzip -c "${BACKUP_FILE}" | docker exec -i ${DB_CONTAINER_NAME} psql -U ${DB_USER} -d ${DB_NAME}

echo "Restore complete! Run Alembic migrations and application health checks to verify integrity."
