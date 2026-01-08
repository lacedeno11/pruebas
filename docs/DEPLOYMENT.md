# Policy Validation Copilot - Deployment Guide

This document provides comprehensive deployment instructions for the Policy Validation Copilot system across different environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Monitoring Setup](#monitoring-setup)
- [Security Configuration](#security-configuration)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)

## Prerequisites

### System Requirements

- **CPU**: Minimum 4 cores, Recommended 8+ cores
- **Memory**: Minimum 8GB RAM, Recommended 16GB+ RAM
- **Storage**: Minimum 50GB, Recommended 100GB+ SSD
- **Network**: Stable internet connection for external services

### Software Dependencies

- **Docker**: Version 20.10+ with Docker Compose
- **Kubernetes**: Version 1.24+ (for production deployment)
- **kubectl**: Compatible with your Kubernetes cluster
- **Helm**: Version 3.8+ (optional, for package management)
- **Python**: Version 3.11+ (for local development)

### External Services

- **PostgreSQL**: Version 14+ for data persistence
- **Redis**: Version 6+ for caching and queues
- **Object Storage**: AWS S3 or compatible service
- **Vector Database**: ChromaDB or Pinecone for RAG
- **SMTP Server**: For email notifications
- **Slack/Teams**: For team notifications (optional)

## Environment Configuration

### Configuration Files

The system uses a hierarchical configuration system:

```
config/
├── .env                    # Base configuration
├── .env.development        # Development overrides
├── .env.testing           # Testing overrides
├── .env.staging           # Staging overrides
├── .env.production        # Production overrides
└── .env.local             # Local overrides (not in git)
```

### Environment Variables

#### Core Application Settings

```bash
# Application
APP_ENVIRONMENT=production
APP_DEBUG=false
APP_LOG_LEVEL=INFO
APP_HOST=0.0.0.0
APP_PORT=8000

# Database
DB_HOST=postgresql
DB_PORT=5432
DB_NAME=policy_copilot
DB_USERNAME=policy_copilot_user
DB_PASSWORD=secure_password_here
DB_SSL_MODE=require

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=secure_redis_password
REDIS_DATABASE=0

# Security
SECURITY_JWT_SECRET_KEY=your_jwt_secret_key_here
SECURITY_ENCRYPTION_KEY=your_32_character_encryption_key
SECURITY_HASH_SALT=your_hash_salt_here
```

#### External Services

```bash
# AWS S3 Storage
STORAGE_BACKEND=s3
STORAGE_S3_BUCKET_NAME=policy-copilot-storage
STORAGE_S3_REGION=us-east-1
STORAGE_S3_ACCESS_KEY=your_aws_access_key
STORAGE_S3_SECRET_KEY=your_aws_secret_key

# Vector Database (ChromaDB)
VECTORDB_BACKEND=chromadb
VECTORDB_CHROMADB_HOST=chromadb
VECTORDB_CHROMADB_PORT=8000

# Or Pinecone (alternative)
VECTORDB_BACKEND=pinecone
VECTORDB_PINECONE_API_KEY=your_pinecone_api_key
VECTORDB_PINECONE_ENVIRONMENT=us-east1-gcp
VECTORDB_PINECONE_INDEX_NAME=policy-documents

# Notifications
NOTIFICATION_SMTP_HOST=smtp.gmail.com
NOTIFICATION_SMTP_PORT=587
NOTIFICATION_SMTP_USERNAME=your_email@gmail.com
NOTIFICATION_SMTP_PASSWORD=your_app_password
NOTIFICATION_FROM_EMAIL=noreply@yourcompany.com

NOTIFICATION_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
```

## Local Development

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd policy-copilot
   ```

2. **Set up Python environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install -e .
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env.local
   # Edit .env.local with your local settings
   ```

4. **Start dependencies with Docker Compose**:
   ```bash
   docker-compose up -d postgresql redis chromadb
   ```

5. **Run database migrations**:
   ```bash
   python -m policy_copilot.database.migrations upgrade
   ```

6. **Start the application**:
   ```bash
   uvicorn policy_copilot.api.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Development Services

Access the following services during development:

- **API Documentation**: http://localhost:8000/docs
- **API Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **ChromaDB**: http://localhost:8001

## Docker Deployment

### Single-Node Deployment

1. **Build the application image**:
   ```bash
   docker build -t policy-copilot:latest .
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your production settings
   ```

3. **Start all services**:
   ```bash
   docker-compose up -d
   ```

4. **Verify deployment**:
   ```bash
   docker-compose ps
   curl http://localhost:8000/health
   ```

### Multi-Service Architecture

The Docker Compose setup includes:

- **API Server**: Main application API (port 8000)
- **Worker**: Background task processor
- **Scheduler**: Scheduled task manager
- **PostgreSQL**: Primary database (port 5432)
- **Redis**: Cache and message broker (port 6379)
- **ChromaDB**: Vector database (port 8001)
- **Prometheus**: Metrics collection (port 9090)
- **Grafana**: Monitoring dashboards (port 3000)

### Docker Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api
docker-compose logs -f worker

# Scale workers
docker-compose up -d --scale worker=3

# Stop services
docker-compose down

# Rebuild and restart
docker-compose up -d --build
```

## Kubernetes Deployment

### Prerequisites

1. **Kubernetes cluster** (1.24+)
2. **kubectl** configured for your cluster
3. **Container registry** access
4. **Persistent storage** provisioner

### Deployment Steps

1. **Build and push container image**:
   ```bash
   # Build multi-stage image
   docker build -t your-registry/policy-copilot:v1.0.0 .
   
   # Push to registry
   docker push your-registry/policy-copilot:v1.0.0
   ```

2. **Create namespace and resources**:
   ```bash
   # Apply Kubernetes manifests
   kubectl apply -f k8s/namespace.yaml
   kubectl apply -f k8s/configmap.yaml
   kubectl apply -f k8s/secrets.yaml
   kubectl apply -f k8s/services.yaml
   kubectl apply -f k8s/deployments.yaml
   ```

3. **Configure secrets** (replace placeholder values):
   ```bash
   # Update secrets with real values
   kubectl edit secret policy-copilot-secrets -n policy-copilot
   
   # Or create from command line
   kubectl create secret generic policy-copilot-secrets \
     --from-literal=DB_PASSWORD=your_db_password \
     --from-literal=SECURITY_JWT_SECRET_KEY=your_jwt_secret \
     -n policy-copilot
   ```

4. **Verify deployment**:
   ```bash
   # Check pod status
   kubectl get pods -n policy-copilot
   
   # Check services
   kubectl get services -n policy-copilot
   
   # View logs
   kubectl logs -f deployment/policy-copilot-api -n policy-copilot
   ```

### Scaling

```bash
# Scale API servers
kubectl scale deployment policy-copilot-api --replicas=5 -n policy-copilot

# Scale workers
kubectl scale deployment policy-copilot-worker --replicas=3 -n policy-copilot

# Auto-scaling (HPA)
kubectl autoscale deployment policy-copilot-api \
  --cpu-percent=70 --min=2 --max=10 -n policy-copilot
```

### Ingress Configuration

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: policy-copilot-ingress
  namespace: policy-copilot
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  tls:
  - hosts:
    - api.policy-copilot.example.com
    secretName: policy-copilot-tls
  rules:
  - host: api.policy-copilot.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: nginx-proxy
            port:
              number: 80
```

## Monitoring Setup

### Prometheus Configuration

1. **Deploy Prometheus**:
   ```bash
   # Using Helm
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm install prometheus prometheus-community/kube-prometheus-stack \
     --namespace monitoring --create-namespace \
     --values monitoring/prometheus-values.yaml
   ```

2. **Configure scraping**:
   - Copy `monitoring/prometheus.yml` to your Prometheus configuration
   - Ensure service discovery is configured for Kubernetes

### Grafana Dashboards

1. **Access Grafana**:
   ```bash
   kubectl port-forward svc/prometheus-grafana 3000:80 -n monitoring
   # Open http://localhost:3000
   ```

2. **Import dashboards**:
   - Policy Copilot Overview: Dashboard ID 12345
   - API Performance: Dashboard ID 12346
   - ML Services: Dashboard ID 12347
   - Infrastructure: Dashboard ID 12348

### Alerting

1. **Configure AlertManager**:
   ```yaml
   # alertmanager.yml
   global:
     smtp_smarthost: 'smtp.gmail.com:587'
     smtp_from: 'alerts@yourcompany.com'
   
   route:
     group_by: ['alertname']
     group_wait: 10s
     group_interval: 10s
     repeat_interval: 1h
     receiver: 'web.hook'
   
   receivers:
   - name: 'web.hook'
     email_configs:
     - to: 'admin@yourcompany.com'
       subject: 'Policy Copilot Alert: {{ .GroupLabels.alertname }}'
   ```

2. **Test alerts**:
   ```bash
   # Trigger test alert
   curl -X POST http://prometheus:9090/api/v1/alerts
   ```

## Security Configuration

### TLS/SSL Setup

1. **Generate certificates**:
   ```bash
   # Using cert-manager (recommended)
   kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.12.0/cert-manager.yaml
   
   # Or use Let's Encrypt
   kubectl apply -f k8s/cert-issuer.yaml
   ```

2. **Configure TLS termination**:
   - Update ingress with TLS configuration
   - Ensure all internal communication uses TLS

### Network Security

1. **Network Policies**:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: policy-copilot-netpol
     namespace: policy-copilot
   spec:
     podSelector:
       matchLabels:
         app.kubernetes.io/name: policy-copilot
     policyTypes:
     - Ingress
     - Egress
     ingress:
     - from:
       - namespaceSelector:
           matchLabels:
             name: ingress-nginx
     egress:
     - to:
       - namespaceSelector:
           matchLabels:
             name: kube-system
   ```

2. **Pod Security Standards**:
   ```yaml
   apiVersion: v1
   kind: Namespace
   metadata:
     name: policy-copilot
     labels:
       pod-security.kubernetes.io/enforce: restricted
       pod-security.kubernetes.io/audit: restricted
       pod-security.kubernetes.io/warn: restricted
   ```

### Secrets Management

1. **External Secrets Operator** (recommended):
   ```bash
   helm repo add external-secrets https://charts.external-secrets.io
   helm install external-secrets external-secrets/external-secrets \
     --namespace external-secrets-system --create-namespace
   ```

2. **AWS Secrets Manager integration**:
   ```yaml
   apiVersion: external-secrets.io/v1beta1
   kind: SecretStore
   metadata:
     name: aws-secrets-manager
     namespace: policy-copilot
   spec:
     provider:
       aws:
         service: SecretsManager
         region: us-east-1
   ```

## Troubleshooting

### Common Issues

#### 1. Database Connection Issues

**Symptoms**: API fails to start, database connection errors

**Solutions**:
```bash
# Check database connectivity
kubectl exec -it deployment/policy-copilot-api -n policy-copilot -- \
  pg_isready -h postgresql -p 5432

# Check database credentials
kubectl get secret policy-copilot-secrets -n policy-copilot -o yaml

# Verify database is running
kubectl get pods -l app.kubernetes.io/name=postgresql -n policy-copilot
```

#### 2. ML Services Not Responding

**Symptoms**: Classification/anomaly detection timeouts

**Solutions**:
```bash
# Check ML service health
curl http://ml-service:8001/health

# Check resource limits
kubectl describe pod -l app.kubernetes.io/component=ml -n policy-copilot

# Scale ML services
kubectl scale deployment policy-copilot-ml --replicas=3 -n policy-copilot
```

#### 3. High Memory Usage

**Symptoms**: Pods being OOMKilled, high memory alerts

**Solutions**:
```bash
# Check memory usage
kubectl top pods -n policy-copilot

# Increase memory limits
kubectl patch deployment policy-copilot-api -n policy-copilot -p \
  '{"spec":{"template":{"spec":{"containers":[{"name":"api","resources":{"limits":{"memory":"2Gi"}}}]}}}}'

# Enable memory profiling
export PYTHONMALLOC=debug
```

#### 4. Queue Backlog

**Symptoms**: Tasks not processing, queue growing

**Solutions**:
```bash
# Check queue status
kubectl exec -it deployment/policy-copilot-worker -n policy-copilot -- \
  python -c "from policy_copilot.integrations.queue_management import *; print(get_queue_stats())"

# Scale workers
kubectl scale deployment policy-copilot-worker --replicas=5 -n policy-copilot

# Check worker logs
kubectl logs -f deployment/policy-copilot-worker -n policy-copilot
```

### Debugging Commands

```bash
# Get all resources
kubectl get all -n policy-copilot

# Describe problematic pod
kubectl describe pod <pod-name> -n policy-copilot

# Get events
kubectl get events -n policy-copilot --sort-by='.lastTimestamp'

# Port forward for debugging
kubectl port-forward svc/policy-copilot-api 8000:8000 -n policy-copilot

# Execute commands in pod
kubectl exec -it deployment/policy-copilot-api -n policy-copilot -- /bin/bash

# Check resource usage
kubectl top nodes
kubectl top pods -n policy-copilot
```

### Log Analysis

```bash
# Centralized logging with ELK stack
kubectl logs -f deployment/policy-copilot-api -n policy-copilot | jq '.'

# Filter error logs
kubectl logs deployment/policy-copilot-api -n policy-copilot | grep ERROR

# Follow logs from all pods
kubectl logs -f -l app.kubernetes.io/name=policy-copilot -n policy-copilot
```

## Maintenance

### Regular Tasks

#### Daily
- Monitor system health and alerts
- Check queue backlogs
- Review error logs
- Verify backup completion

#### Weekly
- Update security patches
- Review performance metrics
- Clean up old logs
- Test disaster recovery procedures

#### Monthly
- Update dependencies
- Review and rotate secrets
- Capacity planning review
- Security audit

### Backup and Recovery

#### Database Backup

```bash
# Automated backup script
#!/bin/bash
BACKUP_DIR="/backups/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

kubectl exec deployment/postgresql -n policy-copilot -- \
  pg_dump -U postgres policy_copilot | gzip > $BACKUP_DIR/policy_copilot.sql.gz

# Upload to S3
aws s3 cp $BACKUP_DIR/policy_copilot.sql.gz s3://backup-bucket/database/
```

#### Configuration Backup

```bash
# Backup Kubernetes resources
kubectl get all,configmap,secret -n policy-copilot -o yaml > k8s-backup.yaml

# Backup monitoring configuration
kubectl get configmap prometheus-config -n monitoring -o yaml > prometheus-backup.yaml
```

#### Disaster Recovery

1. **Database Recovery**:
   ```bash
   # Restore from backup
   kubectl exec -i deployment/postgresql -n policy-copilot -- \
     psql -U postgres -d policy_copilot < backup.sql
   ```

2. **Application Recovery**:
   ```bash
   # Redeploy from backup
   kubectl apply -f k8s-backup.yaml
   
   # Verify health
   kubectl get pods -n policy-copilot
   curl http://api.policy-copilot.example.com/health
   ```

### Updates and Upgrades

#### Application Updates

```bash
# Build new version
docker build -t policy-copilot:v1.1.0 .
docker push your-registry/policy-copilot:v1.1.0

# Rolling update
kubectl set image deployment/policy-copilot-api \
  api=your-registry/policy-copilot:v1.1.0 -n policy-copilot

# Monitor rollout
kubectl rollout status deployment/policy-copilot-api -n policy-copilot

# Rollback if needed
kubectl rollout undo deployment/policy-copilot-api -n policy-copilot
```

#### Dependency Updates

```bash
# Update Python dependencies
pip-compile requirements.in
docker build -t policy-copilot:latest .

# Update Kubernetes components
helm upgrade prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring --values monitoring/prometheus-values.yaml
```

### Performance Optimization

#### Database Optimization

```sql
-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM cases WHERE status = 'PROCESSING';

-- Create indexes
CREATE INDEX CONCURRENTLY idx_cases_status ON cases(status);
CREATE INDEX CONCURRENTLY idx_cases_created_at ON cases(created_at);

-- Update statistics
ANALYZE;
```

#### Application Optimization

```bash
# Profile memory usage
kubectl exec -it deployment/policy-copilot-api -n policy-copilot -- \
  python -m memory_profiler policy_copilot/api/main.py

# Profile CPU usage
kubectl exec -it deployment/policy-copilot-api -n policy-copilot -- \
  python -m cProfile -o profile.stats policy_copilot/api/main.py
```

## Support and Documentation

### Additional Resources

- **API Documentation**: https://api.policy-copilot.example.com/docs
- **Architecture Guide**: docs/ARCHITECTURE.md
- **Development Guide**: docs/DEVELOPMENT.md
- **Security Guide**: docs/SECURITY.md
- **Monitoring Guide**: docs/MONITORING.md

### Getting Help

- **Issues**: Create GitHub issues for bugs and feature requests
- **Discussions**: Use GitHub Discussions for questions
- **Security**: Email security@yourcompany.com for security issues
- **Emergency**: Contact on-call engineer via PagerDuty

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Code style and standards
- Testing requirements
- Pull request process
- Release procedures

---

**Last Updated**: 2024-01-15
**Version**: 1.0.0
**Maintainer**: Policy Copilot Team
