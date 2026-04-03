# Deployment Examples

Examples for deploying the PostGIS service blueprint in common configurations.

## Local Docker Compose

The simplest deployment path:

```bash
copy .env.example .env
docker compose up --build -d
```

This starts:
- PostGIS database on `localhost:5432`
- FastAPI service on `localhost:8000`

## Standalone PostGIS Container

Run PostGIS without the application service:

```bash
docker run --name spatial-postgres \
  -e POSTGRES_USER=spatial \
  -e POSTGRES_PASSWORD=spatial \
  -e POSTGRES_DB=spatial \
  -p 5432:5432 \
  -d postgis/postgis:16-3.4
```

Then load the schema and seed data:

```bash
psql -h localhost -U spatial -d spatial -f sql/schema.sql
psql -h localhost -U spatial -d spatial -f sql/seed.sql
```

## Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `POSTGRES_USER` | `spatial` | Database user |
| `POSTGRES_PASSWORD` | `spatial` | Database password |
| `POSTGRES_DB` | `spatial` | Database name |
| `DATABASE_URL` | `postgresql://spatial:spatial@localhost:5432/spatial` | Full connection string |

## Health Check Validation

After deployment, verify the service is ready:

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{ "status": "ok" }
```

## Production Considerations

- Use a managed PostgreSQL service with PostGIS extensions enabled
- Set strong passwords via environment variables or secrets
- Enable SSL for database connections in production
- Configure connection pooling for multiple concurrent clients
- Add database backups and retention policies before going live
