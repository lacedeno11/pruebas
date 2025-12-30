# DERCAS-ONCO-XAI V1 Operations Runbook

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.12+
- Node.js 18+
- Git

### Initial Setup

1. **Clone and Setup Environment**
   ```bash
   git clone <repository-url>
   cd oncology-xai
   cp .env.example .env
   # Edit .env with your configuration
   ```

2. **Start Infrastructure**
   ```bash
   make up
   ```

3. **Install Dependencies**
   ```bash
   make install-deps
   ```

4. **Run Database Migrations**
   ```bash
   make migrate
   ```

5. **Check Service Health**
   ```bash
   make health
   ```

6. **Access the Application**
   - WebApp: http://localhost:3000
   - API Gateway: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Service Management

### Starting Services

**All Services:**
```bash
make up
```

**Individual Services:**
```bash
make api-gateway      # Port 8000
make case-service     # Port 8001
make image-service    # Port 8002
make inference-service # Port 8003
make ehr-service      # Port 8004
make graph-service    # Port 8005
make ontology-admin-service # Port 8006
make audit-service    # Port 8007
make webapp           # Port 3000
```

### Stopping Services
```bash
make down
```

### Viewing Logs
```bash
make logs
```

## Infrastructure Components

### PostgreSQL Database
- **Host:** localhost:5432
- **Database:** oncology_db
- **User:** oncology_user
- **Password:** oncology_pass (change in production)

**Connection:**
```bash
psql -h localhost -p 5432 -U oncology_user -d oncology_db
```

### RabbitMQ Message Broker
- **Management UI:** http://localhost:15672
- **Username:** guest
- **Password:** guest
- **AMQP Port:** 5672

### Redis Cache
- **Host:** localhost:6379
- **Database:** 0

**Connection:**
```bash
redis-cli -h localhost -p 6379
```

### MinIO Object Storage
- **Console:** http://localhost:9001
- **API:** http://localhost:9000
- **Username:** minioadmin
- **Password:** minioadmin

### Keycloak Authentication
- **Admin Console:** http://localhost:8080
- **Realm:** oncology-xai
- **Admin User:** admin
- **Admin Password:** admin

### Apache Jena Fuseki (RDF Triple Store)
- **Web Interface:** http://localhost:3030
- **Dataset:** oncology
- **SPARQL Endpoint:** http://localhost:3030/oncology/sparql

### Jaeger Tracing
- **UI:** http://localhost:16686

### Prometheus Metrics
- **UI:** http://localhost:9090

## Development Workflow

### Code Quality
```bash
# Format code
make fmt

# Run linting
make lint

# Run tests
make test
```

### Database Operations

**Create Migration:**
```bash
cd apps/<service-name>
alembic revision --autogenerate -m "Description"
```

**Apply Migrations:**
```bash
make migrate
```

**Reset Database:**
```bash
make down
docker volume prune -f
make up
make migrate
```

### Debugging

**Service Logs:**
```bash
docker-compose -f infra/docker-compose.yml logs -f <service-name>
```

**Database Queries:**
```bash
# Connect to database
psql -h localhost -p 5432 -U oncology_user -d oncology_db

# Common queries
SELECT * FROM patients LIMIT 10;
SELECT * FROM cases WHERE status = 'PROCESSING';
SELECT * FROM audit_events ORDER BY timestamp DESC LIMIT 20;
```

**Message Queue Inspection:**
- Access RabbitMQ Management UI at http://localhost:15672
- Check queue depths and message rates
- Monitor dead letter queues

## Troubleshooting

### Common Issues

**Port Conflicts:**
```bash
# Check what's using a port
lsof -i :8000

# Kill process using port
kill -9 $(lsof -t -i:8000)
```

**Database Connection Issues:**
```bash
# Check if PostgreSQL is running
docker-compose -f infra/docker-compose.yml ps postgres

# Restart PostgreSQL
docker-compose -f infra/docker-compose.yml restart postgres
```

**Storage Issues:**
```bash
# Check MinIO status
docker-compose -f infra/docker-compose.yml ps minio

# Check bucket exists
mc alias set local http://localhost:9000 minioadmin minioadmin
mc ls local/
```

**Memory Issues:**
```bash
# Check container memory usage
docker stats

# Increase Docker memory limits in Docker Desktop
```

### Service-Specific Troubleshooting

**API Gateway:**
- Check JWT token validation
- Verify Keycloak connectivity
- Check rate limiting configuration

**Inference Service:**
- Monitor Celery worker status
- Check GPU availability (if using real models)
- Verify model loading

**EHR Service:**
- Check LLM provider configuration
- Verify ontology loading
- Monitor entity extraction performance

**Graph Service:**
- Check Fuseki connectivity
- Verify SPARQL query performance
- Monitor graph construction jobs

### Performance Monitoring

**Key Metrics to Monitor:**
- API response times
- Database query performance
- Message queue depths
- Storage usage
- Memory and CPU utilization

**Prometheus Queries:**
```promql
# API request rate
rate(http_requests_total[5m])

# Database connection pool
db_connections_active

# Queue depth
rabbitmq_queue_messages
```

## Security Considerations

### Development Environment
- Default passwords are used (change for production)
- CORS is permissive for development
- Debug mode is enabled

### Production Checklist
- [ ] Change all default passwords
- [ ] Configure proper CORS origins
- [ ] Disable debug mode
- [ ] Set up proper TLS certificates
- [ ] Configure firewall rules
- [ ] Set up log aggregation
- [ ] Configure backup procedures
- [ ] Set up monitoring alerts

## Backup and Recovery

### Database Backup
```bash
# Create backup
pg_dump -h localhost -p 5432 -U oncology_user oncology_db > backup.sql

# Restore backup
psql -h localhost -p 5432 -U oncology_user oncology_db < backup.sql
```

### Object Storage Backup
```bash
# Sync MinIO bucket
mc mirror local/oncology-xai /backup/minio/
```

### Configuration Backup
- Back up `.env` file
- Back up Keycloak realm configuration
- Back up custom ontology files

## Maintenance

### Regular Tasks
- Monitor disk space usage
- Review audit logs
- Update dependencies
- Check for security updates
- Validate backup procedures

### Log Rotation
- Configure log rotation for all services
- Archive old audit logs
- Clean up temporary files

### Health Checks
```bash
# Automated health check
make health

# Manual service verification
curl http://localhost:8000/healthz
curl http://localhost:8001/healthz
# ... for all services
```

## Contact and Support

### Development Team
- Architecture questions: See docs/architecture.md
- API documentation: http://localhost:8000/docs
- Issue tracking: GitHub Issues

### Emergency Procedures
1. Check service health: `make health`
2. Review recent logs: `make logs`
3. Check infrastructure status
4. Escalate to development team if needed

This runbook provides the essential information for operating the DERCAS-ONCO-XAI V1 platform in development and production environments.
