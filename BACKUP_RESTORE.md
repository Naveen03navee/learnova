# Learnova Database Backup & Restore Operations

Maintaining regular backups and verifying restores is critical for protecting the Learnova Knowledge Base and Question Banks.

## Automated Backups
Learnova includes an automated backup script `scripts/db_backup.sh`. 

### Configuration
You can configure the behavior via environment variables:
- `BACKUP_DIR`: Directory to store backups (default: `./backups`)
- `RETENTION_DAYS`: Number of days to keep backups (default: `7`)
- `DB_CONTAINER_NAME`: The Docker container name for the database (default: `learnova-db-1`)

### Scheduling via Cron
To automate backups, add the following to the host server's crontab (e.g. `crontab -e`) to run daily at 2:00 AM:
```cron
0 2 * * * /path/to/learnova/scripts/db_backup.sh >> /var/log/learnova_backup.log 2>&1
```

## Restore Testing & Execution
A backup is only valid if it can be restored. You must periodically perform a dry-run restore.

### Executing a Restore
> [!CAUTION]
> The restore script drops the existing database entirely before restoring. Ensure you are restoring to the correct environment.

Run the restore script:
```bash
./scripts/db_restore.sh <container_name> ./backups/learnova_backup_20240101_020000.sql.gz
```

### Validation Steps post-Restore
After a restore completes, verify the integrity of the data:
1. Ensure the `pgvector` extension exists: `\dx` in psql.
2. Ensure the `vector` type columns have `384` dimensions for MMR and Deduplication:
   ```sql
   SELECT attname, atttypmod FROM pg_attribute WHERE attrelid = 'questions'::regclass AND attname = 'embedding';
   ```
3. Boot the application backend.
4. Call the health endpoint: `curl http://localhost:8000/api/v1/health/ready`.
5. Login and manually verify Exams, Subjects, Resources, and Question Papers.
