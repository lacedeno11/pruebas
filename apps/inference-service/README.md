# Inference Service

FastAPI service for ML inference and explainable AI in DERCAS-ONCO-XAI V1 platform.

## Responsibilities

- Asynchronous ML processing with Celery workers
- Mock pattern models for 5 patterns (lepidic, acinar, papillary, micropapillary, solid)
- Mock mutation models for 3 mutations (EGFR, KRAS, TP53)
- ImageAnalysisGraph LangGraph workflow implementation
- XAI artifact generation (overlays, heatmaps)
- Clinical guardrails and HITL policies

## LangGraph Workflow: ImageAnalysisGraph

ValidateInput → LoadImage → RunPatternModel → RunMutationModel → GenerateXAI → AssembleResultBundle → PolicyCheck → PersistAndAudit → Finalize

## Endpoints

- `POST /api/v1/images/{imageId}:process` - Start ML processing
- `GET /api/v1/jobs/{jobId}` - Get job status and progress
- `GET /api/v1/images/{imageId}/results/latest` - Get latest results
- `GET /api/v1/results/{resultBundleId}` - Get result bundle
- `GET /api/v1/results/{resultBundleId}/artifacts` - Get XAI artifacts

## Development

```bash
cd apps/inference-service
python -m uvicorn main:app --reload --port 8003
```
