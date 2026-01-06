# DERCAS-ONCO-XAI V1 - Operations Runbook

## Overview

This runbook provides operational procedures for deploying, monitoring, and troubleshooting the DERCAS-ONCO-XAI V1 platform.

## Quick Reference

### Essential Commands

```bash
# Start the platform
make up

# Check service health
make health

# View logs
make logs

# Stop the platform
make down

# Clean restart
make clean && make up

# Run tests
make test

# Code quality
make lint && make fmt
```

### Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| API Gateway | http://localhost:8080 | JWT required |
| WebApp | http://localhost:3000 | Keycloak login |
| Keycloak Admin | http://localhost:8081/admin | admin/admin |
| RabbitMQ Management | http://localhost:15672 | guest/guest |
| MinIO Console | http://localhost:9001 | minioadmin/minioadmin |
| Fuseki | http://localhost:3030 | admin/fuseki_admin |
| Prometheus | http://localhost:9090 | No auth |
| Jaeger | http://localhost:16686 | No auth |

## Deployment Procedures

### Local Development Setup

#### Prerequisites

- Docker 20.10+ with Docker Compose
- Python 3.12+
- Node.js 18+
- Make utility
- Git

#### Initial Setup

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd oncology-xai
   ```

2. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your specific configuration
   ```

3. **Development Setup**
   ```bash
   make dev-setup
   ```

4. **Start Infrastructure**
   ```bash
   make up
   ```

5. **Verify Deployment**
   ```bash
   make health
   ```

#### Service-by-Service Startup

If you need to start services individually:

```bash
# Infrastructure only
docker-compose -f infra/docker-compose.yml up -d postgres rabbitmq redis minio keycloak fuseki jaeger prometheus

# Individual services
cd apps/api-gateway && uvicorn src.main:app --reload --port 8080
cd apps/case-service && uvicorn src.main:app --reload --port 8001
# ... repeat for other services
```

### Production Deployment

#### Container Registry Setup

```bash
# Build and tag images
make build

# Tag for registry
docker tag oncology-xai/api-gateway:latest registry.example.com/oncology-xai/api-gateway:v1.0.0

# Push to registry
docker push registry.example.com/oncology-xai/api-gateway:v1.0.0
```

#### Kubernetes Deployment

```bash
# Apply namespace
kubectl create namespace oncology-xai

# Apply secrets
kubectl apply -f k8s/secrets/

# Apply infrastructure
kubectl apply -f k8s/infrastructure/

# Apply services
kubectl apply -f k8s/services/

# Apply ingress
kubectl apply -f k8s/ingress/
```

#### Health Check Verification

```bash
# Check all pods
kubectl get pods -n oncology-xai

# Check services
kubectl get svc -n oncology-xai

# Check ingress
kubectl get ingress -n oncology-xai

# Check logs
kubectl logs -f deployment/api-gateway -n oncology-xai
```

## Monitoring and Observability

### Health Monitoring

#### Service Health Checks

```bash
# Automated health check
make health

# Manual health checks
curl -f http://localhost:8080/healthz
curl -f http://localhost:8001/healthz
curl -f http://localhost:8002/healthz
# ... for each service
```

#### Infrastructure Health

```bash
# PostgreSQL
docker exec -it oncology-postgres pg_isready -U oncology_user

# RabbitMQ
curl -u guest:guest http://localhost:15672/api/overview

# Redis
docker exec -it oncology-redis redis-cli ping

# MinIO
curl http://localhost:9000/minio/health/live

# Keycloak
curl http://localhost:8081/health

# Fuseki
curl http://localhost:3030/$/ping
```

### Metrics and Monitoring

#### Prometheus Metrics

Access Prometheus at http://localhost:9090

**Key Metrics to Monitor:**

```promql
# Service availability
up{job="oncology-services"}

# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Response time
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Database connections
pg_stat_database_numbackends

# Queue depth
rabbitmq_queue_messages

# Memory usage
process_resident_memory_bytes

# CPU usage
rate(process_cpu_seconds_total[5m])
```

#### Distributed Tracing

Access Jaeger at http://localhost:16686

**Trace Analysis:**
- Search by service name
- Filter by operation
- Analyze latency patterns
- Identify bottlenecks
- Debug error flows

### Log Management

#### Centralized Logging

```bash
# View all service logs
make logs

# View specific service logs
docker-compose -f infra/docker-compose.yml logs -f api-gateway

# Follow logs with grep
docker-compose -f infra/docker-compose.yml logs -f | grep ERROR

# Export logs
docker-compose -f infra/docker-compose.yml logs --since 1h > logs_$(date +%Y%m%d_%H%M%S).txt
```

#### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General operational messages
- **WARNING**: Potentially harmful situations
- **ERROR**: Error events that allow application to continue
- **CRITICAL**: Serious error events that may cause termination

#### Structured Logging Format

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "service": "api-gateway",
  "correlation_id": "corr_123456",
  "case_id": "case_789",
  "user_id": "user_abc",
  "message": "Request processed successfully",
  "duration_ms": 150,
  "status_code": 200
}
```

## Troubleshooting Guide

### Common Issues

#### 1. Services Not Starting

**Symptoms:**
- Docker containers failing to start
- Port conflicts
- Connection refused errors

**Diagnosis:**
```bash
# Check container status
docker-compose -f infra/docker-compose.yml ps

# Check container logs
docker-compose -f infra/docker-compose.yml logs <service-name>

# Check port usage
netstat -tulpn | grep <port>

# Check Docker resources
docker system df
docker system events
```

**Solutions:**
```bash
# Free up ports
sudo lsof -ti:<port> | xargs kill -9

# Clean Docker resources
docker system prune -f
docker volume prune -f

# Restart Docker daemon
sudo systemctl restart docker

# Increase Docker resources (Docker Desktop)
# Settings > Resources > Advanced
```

#### 2. Database Connection Issues

**Symptoms:**
- Connection timeout errors
- Authentication failures
- Database not ready

**Diagnosis:**
```bash
# Check PostgreSQL status
docker exec -it oncology-postgres pg_isready -U oncology_user

# Test connection
docker exec -it oncology-postgres psql -U oncology_user -d oncology_db -c "SELECT 1;"

# Check database logs
docker logs oncology-postgres
```

**Solutions:**
```bash
# Reset database
docker-compose -f infra/docker-compose.yml down -v
docker-compose -f infra/docker-compose.yml up -d postgres

# Run migrations
cd apps/case-service && alembic upgrade head

# Check connection string
echo $POSTGRES_DSN
```

#### 3. Authentication Issues

**Symptoms:**
- 401 Unauthorized errors
- JWT validation failures
- Keycloak connection issues

**Diagnosis:**
```bash
# Check Keycloak status
curl http://localhost:8081/health

# Test token endpoint
curl -X POST http://localhost:8081/realms/oncology-realm/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials&client_id=oncology-client&client_secret=your-secret"

# Check JWKS endpoint
curl http://localhost:8081/realms/oncology-realm/protocol/openid-connect/certs
```

**Solutions:**
```bash
# Restart Keycloak
docker-compose -f infra/docker-compose.yml restart keycloak

# Import realm configuration
docker exec -it oncology-keycloak /opt/keycloak/bin/kc.sh import --file /opt/keycloak/data/import/realm-export.json

# Update client secret in .env
```

#### 4. Message Queue Issues

**Symptoms:**
- Events not being processed
- Queue buildup
- Connection failures

**Diagnosis:**
```bash
# Check RabbitMQ status
curl -u guest:guest http://localhost:15672/api/overview

# Check queue status
curl -u guest:guest http://localhost:15672/api/queues

# Check connections
curl -u guest:guest http://localhost:15672/api/connections
```

**Solutions:**
```bash
# Restart RabbitMQ
docker-compose -f infra/docker-compose.yml restart rabbitmq

# Purge queues
curl -u guest:guest -X DELETE http://localhost:15672/api/queues/%2F/queue-name/contents

# Reset RabbitMQ data
docker-compose -f infra/docker-compose.yml down
docker volume rm oncology-xai_rabbitmq_data
docker-compose -f infra/docker-compose.yml up -d rabbitmq
```

#### 5. Object Storage Issues

**Symptoms:**
- Image upload failures
- Access denied errors
- Bucket not found

**Diagnosis:**
```bash
# Check MinIO status
curl http://localhost:9000/minio/health/live

# Test bucket access
docker exec -it oncology-minio mc ls local/oncology-data

# Check bucket policy
docker exec -it oncology-minio mc policy get local/oncology-data
```

**Solutions:**
```bash
# Create missing buckets
docker exec -it oncology-minio mc mb local/oncology-data
docker exec -it oncology-minio mc mb local/oncology-images

# Set bucket policy
docker exec -it oncology-minio mc policy set public local/oncology-data

# Reset MinIO data
docker-compose -f infra/docker-compose.yml down
docker volume rm oncology-xai_minio_data
docker-compose -f infra/docker-compose.yml up -d minio
```

#### 6. ML Processing Issues

**Symptoms:**
- Jobs stuck in queue
- Model loading failures
- GPU not available

**Diagnosis:**
```bash
# Check Celery workers
docker exec -it oncology-inference celery -A src.worker inspect active

# Check job status
curl http://localhost:8003/api/v1/jobs/<job-id>

# Check GPU availability (if applicable)
nvidia-smi
```

**Solutions:**
```bash
# Restart Celery workers
docker-compose -f infra/docker-compose.yml restart inference-service

# Clear job queue
docker exec -it oncology-redis redis-cli FLUSHDB

# Check model files
docker exec -it oncology-inference ls -la /app/models/
```

### Performance Issues

#### High Memory Usage

**Diagnosis:**
```bash
# Check container memory usage
docker stats

# Check system memory
free -h
top -o %MEM
```

**Solutions:**
```bash
# Increase Docker memory limits
# Edit docker-compose.yml memory limits

# Optimize database connections
# Reduce DB_POOL_SIZE in .env

# Clear caches
docker exec -it oncology-redis redis-cli FLUSHALL
```

#### High CPU Usage

**Diagnosis:**
```bash
# Check container CPU usage
docker stats

# Check system CPU
top -o %CPU
htop
```

**Solutions:**
```bash
# Scale services horizontally
docker-compose -f infra/docker-compose.yml up -d --scale inference-service=3

# Optimize worker concurrency
# Adjust CELERY_WORKER_CONCURRENCY in .env

# Profile application code
# Use profiling tools in development
```

#### Slow Database Queries

**Diagnosis:**
```bash
# Enable query logging
docker exec -it oncology-postgres psql -U oncology_user -d oncology_db -c "ALTER SYSTEM SET log_statement = 'all';"

# Check slow queries
docker exec -it oncology-postgres psql -U oncology_user -d oncology_db -c "SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"
```

**Solutions:**
```bash
# Add database indexes
# Review and optimize SQL queries
# Consider read replicas for heavy read workloads
```

## Backup and Recovery

### Database Backup

#### Automated Backup

```bash
# Create backup script
cat > backup_db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups/postgres"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/oncology_db_$TIMESTAMP.sql"

mkdir -p $BACKUP_DIR
docker exec oncology-postgres pg_dump -U oncology_user oncology_db > $BACKUP_FILE
gzip $BACKUP_FILE

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
EOF

chmod +x backup_db.sh

# Schedule with cron
echo "0 2 * * * /path/to/backup_db.sh" | crontab -
```

#### Manual Backup

```bash
# Full database backup
docker exec oncology-postgres pg_dump -U oncology_user oncology_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Specific table backup
docker exec oncology-postgres pg_dump -U oncology_user -t patients oncology_db > patients_backup.sql
```

#### Database Restore

```bash
# Restore from backup
docker exec -i oncology-postgres psql -U oncology_user oncology_db < backup_file.sql

# Restore specific table
docker exec -i oncology-postgres psql -U oncology_user oncology_db < patients_backup.sql
```

### Object Storage Backup

```bash
# Backup MinIO data
docker exec oncology-minio mc mirror local/oncology-data /backup/minio/

# Restore MinIO data
docker exec oncology-minio mc mirror /backup/minio/ local/oncology-data
```

### Configuration Backup

```bash
# Backup configuration files
tar -czf config_backup_$(date +%Y%m%d_%H%M%S).tar.gz .env infra/ docs/

# Backup Keycloak realm
curl -u admin:admin http://localhost:8081/admin/realms/oncology-realm > realm_backup.json
```

## Security Procedures

### Security Monitoring

#### Access Monitoring

```bash
# Monitor failed login attempts
grep "authentication failed" /var/log/keycloak/keycloak.log

# Monitor API access patterns
grep "401\|403" /var/log/api-gateway/access.log

# Check for suspicious activity
grep -E "(SQL injection|XSS|CSRF)" /var/log/*/security.log
```

#### Vulnerability Scanning

```bash
# Scan Docker images
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image oncology-xai/api-gateway:latest

# Scan dependencies
cd apps/api-gateway && safety check

# Network scanning
nmap -sV localhost
```

### Security Updates

#### Regular Updates

```bash
# Update base images
docker pull python:3.12-slim
docker pull postgres:16
docker pull rabbitmq:3-management

# Rebuild with updated images
make build

# Update Python dependencies
cd apps/api-gateway && pip-audit --fix
```

#### Security Patches

```bash
# Apply security patches
apt update && apt upgrade -y

# Update Docker
curl -fsSL https://get.docker.com | sh

# Update Kubernetes
kubeadm upgrade plan
kubeadm upgrade apply
```

### Incident Response

#### Security Incident Procedure

1. **Immediate Response**
   - Isolate affected systems
   - Preserve evidence
   - Notify stakeholders

2. **Investigation**
   - Analyze logs and traces
   - Identify attack vectors
   - Assess damage

3. **Containment**
   - Block malicious traffic
   - Revoke compromised credentials
   - Apply emergency patches

4. **Recovery**
   - Restore from clean backups
   - Implement additional controls
   - Monitor for reoccurrence

5. **Post-Incident**
   - Document lessons learned
   - Update procedures
   - Conduct training

## Maintenance Procedures

### Regular Maintenance Tasks

#### Daily Tasks

```bash
# Check service health
make health

# Monitor disk space
df -h

# Check error logs
grep ERROR /var/log/oncology-xai/*.log

# Verify backups
ls -la /backups/postgres/
```

#### Weekly Tasks

```bash
# Update dependencies
cd apps/ && for dir in */; do cd "$dir" && pip list --outdated && cd ..; done

# Clean up old logs
find /var/log/oncology-xai/ -name "*.log" -mtime +7 -delete

# Database maintenance
docker exec oncology-postgres psql -U oncology_user -d oncology_db -c "VACUUM ANALYZE;"

# Clean Docker resources
docker system prune -f
```

#### Monthly Tasks

```bash
# Security updates
apt update && apt list --upgradable

# Performance review
# Analyze Prometheus metrics
# Review slow query logs
# Check resource utilization

# Backup verification
# Test restore procedures
# Verify backup integrity

# Documentation updates
# Update runbook
# Review procedures
# Update contact information
```

### Capacity Planning

#### Resource Monitoring

```bash
# CPU utilization
sar -u 1 10

# Memory usage
free -h && cat /proc/meminfo

# Disk I/O
iostat -x 1 10

# Network traffic
iftop -i eth0
```

#### Scaling Decisions

**Scale Up Indicators:**
- CPU usage > 80% sustained
- Memory usage > 85%
- Disk I/O wait > 20%
- Response time > SLA

**Scale Out Indicators:**
- Queue depth increasing
- Request rate growing
- Geographic distribution needs

## Contact Information

### Emergency Contacts

| Role | Name | Phone | Email |
|------|------|-------|-------|
| Platform Lead | [Name] | [Phone] | [Email] |
| DevOps Engineer | [Name] | [Phone] | [Email] |
| Security Officer | [Name] | [Phone] | [Email] |
| Clinical Lead | [Name] | [Phone] | [Email] |

### Escalation Procedures

1. **Level 1**: Development Team (Response: 1 hour)
2. **Level 2**: Platform Team (Response: 30 minutes)
3. **Level 3**: Management (Response: 15 minutes)
4. **Level 4**: Executive (Response: Immediate)

### External Support

| Service | Contact | SLA |
|---------|---------|-----|
| Cloud Provider | [Contact] | 24/7 |
| Database Support | [Contact] | Business Hours |
| Security Vendor | [Contact] | 24/7 |

## Appendices

### A. Configuration Templates

See `infra/` directory for Docker Compose templates and Kubernetes manifests.

### B. Monitoring Dashboards

Grafana dashboard configurations available in `infra/grafana/dashboards/`.

### C. Automation Scripts

Deployment and maintenance scripts available in `scripts/` directory.

### D. Compliance Checklists

Security and compliance checklists available in `docs/compliance/`.
