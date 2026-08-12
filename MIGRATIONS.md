# Database Migrations Deployment Strategy

Learnova uses **Alembic** to manage PostgreSQL database migrations. 

## Deployment Pipeline
Migrations must be strictly managed to prevent downtime or database corruption.

### Pre-Deployment Checks
1. Ensure a full automated backup has run and completed successfully immediately prior to deployment.
2. Verify all backend connection pools are drained or application traffic is paused.

### Execution
Run the migrations from within the backend Docker container before enabling application traffic:
```bash
docker-compose exec backend alembic upgrade head
```

### Rollback Strategy
If a migration fails during deployment (e.g. timeout, syntax error, missing index):

1. **Abort Deployment**: Stop routing traffic to the new backend containers.
2. **Determine Failure State**: 
   - Use `alembic current` to see the current revision.
   - If the database is in a half-migrated state, attempting an `alembic downgrade -1` might fail depending on transactional DDL support.
3. **Primary Rollback (Alembic)**:
   ```bash
   docker-compose exec backend alembic downgrade <previous_revision>
   ```
4. **Catastrophic Rollback (Restore)**:
   If the database schema is corrupted or data was lost during the migration, utilize the pre-deployment backup immediately via `scripts/db_restore.sh`. 

### Best Practices
- Never manually manipulate the `alembic_version` table in production.
- All new migrations must be tested on a staging clone of the production database before live deployment.
