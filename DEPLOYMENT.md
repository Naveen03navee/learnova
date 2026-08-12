# Learnova Deployment Strategy

Learnova is designed to be platform-agnostic, using Docker to isolate the application environment. The stack consists of:
- **FastAPI Backend**: Python 3.11 based container executing Uvicorn.
- **Next.js Frontend**: Node 20 alpine based container executing a production build.
- **PostgreSQL + pgvector**: Relational database with vector similarity search capabilities.
- **Redis**: In-memory store for Pub/Sub messaging (Server-Sent Events) and background task queuing.

## Docker Deployment (Platform Agnostic)

The recommended deployment method for Learnova is via the included `docker-compose.yml` file. This provisions the entire network stack and injects configurations appropriately.

### Pre-requisites
1. A Linux server (Ubuntu 22.04 LTS recommended) with Docker and Docker Compose installed.
2. An external domain pointing to the server's IP address.
3. TLS/SSL Certificates (Let's Encrypt recommended).
4. Environment variables populated in `.env` (refer to `ENVIRONMENT.md`).

### Deployment Steps
1. Clone the repository to the production server.
2. Provide the production variables: `cp .env.example .env` and carefully edit `.env`.
3. Start the application:
   ```bash
   docker-compose up -d --build
   ```
4. Verify all containers are running:
   ```bash
   docker-compose ps
   ```

### Reverse Proxy Configuration
Production environments must enforce HTTPS. Use an Nginx or Traefik reverse proxy to terminate SSL before proxying traffic to:
- Frontend Container on port `3000`
- Backend Container on port `8000` (ensure `/api` requests route to this backend)

### Database Migrations
Always run Alembic migrations prior to allowing traffic into the backend:
```bash
docker-compose exec backend alembic upgrade head
```
If a migration fails, consult `MIGRATIONS.md` for rollback procedures.

## Connection Pooling Limits
The backend utilizes asynchronous SQLAlchemy pools configured via `.env`:
- `DATABASE_POOL_SIZE`: Adjust based on maximum PostgreSQL concurrent connections (e.g. 20)
- `DATABASE_MAX_OVERFLOW`: Allowed surplus connections during traffic spikes (e.g. 10)

If deploying the database externally (e.g. AWS RDS, Supabase Managed), ensure your instance allows connection counts exceeding `(Backend Workers * DATABASE_POOL_SIZE)`.

## High Availability Considerations
For high availability, the backend is stateless (besides Redis PubSub) and can be horizontally scaled. Ensure `Redis` is reachable across all backend nodes so that SSE streaming properly synchronizes generation batches.
