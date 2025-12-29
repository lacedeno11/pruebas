# DERCAS-ONCO-XAI Runbook

## Operations Guide

### Starting the System

```bash
cd oncology-xai/infra

# Start all services
docker compose up -d

# Check service health
docker compose ps
```

### Service Health Checks

Each service exposes a `/healthz` endpoint:

```bash
# Check all services
for port in 8000 8001 8002 8003 8004 8005 8006 8007; do
  echo "Port $port: $(curl -s http://localhost:$port/healthz | jq -r .status)"
done
```

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f case-service

# Last 100 lines with timestamps
docker compose logs --tail=100 -t inference-service
```

### Stopping the System

```bash
# Stop all containers
docker compose down

# Stop and remove volumes (data loss!)
docker compose down -v
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Failures

**Symptoms**: Services fail to start, logs show `Connection refused`

**Solution**:
```bash
# Check PostgreSQL is running
docker compose ps postgres

# View PostgreSQL logs
docker compose logs postgres

# Restart PostgreSQL
docker compose restart postgres

# Wait 10s then restart dependent services
sleep 10 && docker compose restart case-service image-service
```

#### 2. RabbitMQ Queue Backlog

**Symptoms**: Audit events not appearing, high memory usage

**Solution**:
```bash
# Check queue depth
docker compose exec rabbitmq rabbitmqctl list_queues

# Restart audit service consumer
docker compose restart audit-service

# Purge queue (data loss!)
docker compose exec rabbitmq rabbitmqctl purge_queue audit_events
```

#### 3. MinIO Storage Issues

**Symptoms**: Image upload failures, 500 errors

**Solution**:
```bash
# Check MinIO health
curl http://localhost:9000/minio/health/live

# View MinIO logs
docker compose logs minio

# Verify bucket exists
docker compose exec minio mc ls local/oncology-images
```

#### 4. Keycloak Token Issues

**Symptoms**: 401 Unauthorized errors, JWT validation failures

**Solution**:
```bash
# Check Keycloak is ready
curl http://localhost:8080/health/ready

# View Keycloak logs
docker compose logs keycloak

# Restart Keycloak (takes ~60s)
docker compose restart keycloak
```

#### 5. Celery Worker Not Processing Jobs

**Symptoms**: Jobs stuck in "pending" state

**Solution**:
```bash
# Check Redis connection
docker compose exec redis redis-cli ping

# View worker logs
docker compose logs inference-worker

# Restart worker
docker compose restart inference-worker
```

#### 6. Fuseki SPARQL Errors

**Symptoms**: Graph queries returning 500, ontology lookup failures

**Solution**:
```bash
# Check Fuseki health
curl http://localhost:3030/$/ping

# View Fuseki logs
docker compose logs fuseki

# Restart Fuseki
docker compose restart fuseki
```

---

## Scaling

### Horizontal Scaling

```bash
# Scale inference workers
docker compose up -d --scale inference-worker=3

# Scale case service
docker compose up -d --scale case-service=2
```

### Resource Limits

Edit `docker-compose.yml` to adjust resources:

```yaml
services:
  inference-service:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G
```

---

## Backup & Recovery

### Database Backup

```bash
# Backup PostgreSQL
docker compose exec postgres pg_dump -U oncology oncology_xai > backup_$(date +%Y%m%d).sql

# Restore
cat backup_20240101.sql | docker compose exec -T postgres psql -U oncology oncology_xai
```

### MinIO Backup

```bash
# Backup images bucket
docker compose exec minio mc mirror local/oncology-images /backup/images

# Restore
docker compose exec minio mc mirror /backup/images local/oncology-images
```

### Fuseki Backup

```bash
# Backup triple store
docker compose exec fuseki /jena-fuseki/bin/tdbbackup --loc /fuseki/databases/oncology /backup/fuseki
```

---

## Monitoring

### Key Metrics to Watch

| Metric | Warning Threshold | Critical Threshold |
|--------|-------------------|-------------------|
| CPU Usage | 70% | 90% |
| Memory Usage | 80% | 95% |
| Disk Usage | 70% | 90% |
| Request Latency (p99) | 1s | 5s |
| Error Rate | 1% | 5% |
| Queue Depth | 1000 | 10000 |

### Prometheus Queries

```promql
# Request rate by service
sum(rate(http_requests_total[5m])) by (service)

# Error rate
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))

# Inference job duration
histogram_quantile(0.99, rate(inference_job_duration_seconds_bucket[5m]))
```

### Alerting

Configure alerts in Prometheus for:
- Service down (healthz failures)
- High error rate (>5%)
- High latency (p99 > 5s)
- Queue backlog (>10000 messages)
- Disk space (>90% full)

---

## Security

### Rotate Secrets

1. Update secrets in `.env` file
2. Restart affected services
3. Invalidate old tokens in Keycloak

### Keycloak User Management

```bash
# Access Keycloak admin console
open http://localhost:8080/admin

# Create new user via CLI
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh create users \
  -r oncology-xai \
  -s username=newuser \
  -s enabled=true
```

### Audit Log Access

```bash
# Query audit events
curl -s "http://localhost:8007/api/v1/events?case_id=<uuid>" | jq
```

---

## Incident Response

### Severity Levels

| Level | Description | Response Time | Example |
|-------|-------------|---------------|---------|
| P1 | System down | 15 min | All services unreachable |
| P2 | Major feature broken | 1 hour | Inference not working |
| P3 | Minor issue | 4 hours | Slow graph queries |
| P4 | Enhancement | Next sprint | UI improvement |

### Escalation Path

1. On-call engineer investigates
2. If unresolved in 30 min → escalate to team lead
3. If P1/P2 unresolved in 1 hour → escalate to engineering manager

### Post-Incident

1. Create incident report
2. Identify root cause
3. Implement fixes
4. Update runbook if needed
5. Share learnings in team retrospective
