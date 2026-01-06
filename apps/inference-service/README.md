# Inference Service

ML processing service with Celery workers and LangGraph workflows for image analysis.

## Features

- Asynchronous ML processing with Celery workers
- ImageAnalysisGraph LangGraph workflow
- Mock models for 5 histological patterns (lepidic, acinar, papillary, micropapillary, solid)
- Mock models for 3 genetic mutations (EGFR, KRAS, TP53)
- XAI artifact generation (overlays, heatmaps)
- Job status tracking and progress reporting
- Clinical guardrails for low confidence scores

## Endpoints

- `POST /api/v1/images/{imageId}:process` - Start image processing
- `GET /api/v1/jobs/{jobId}` - Get job status and progress
- `GET /api/v1/images/{imageId}/results/latest` - Get latest results
- `GET /api/v1/results/{resultBundleId}` - Get result bundle
- `GET /api/v1/results/{resultBundleId}/artifacts` - Get XAI artifacts

## LangGraph Workflow

```
ValidateInput → LoadImage → RunPatternModel → RunMutationModel → 
GenerateXAI → AssembleResultBundle → PolicyCheck → PersistAndAudit → Finalize
```

## Development

```bash
cd apps/inference-service
pip install -r requirements.txt
alembic upgrade head
celery -A src.worker worker --loglevel=info
uvicorn src.main:app --reload --port 8003
```
