import { Router, Request, Response } from 'express';
import { createApiService } from '../services/ApiService';
import { logger } from '../utils/logger';

const router = Router();
const apiService = createApiService();

// GET /api/telcos/ots - Get OTs from mock TELCOS API
router.get('/ots', async (req: Request, res: Response) => {
  try {
    const ots = await apiService.getOTs();
    res.set('X-Mock-Mode', 'true');
    res.json(ots);
  } catch (error) {
    logger.error('Error fetching OTs from mock API', { error });
    res.status(500).json({ error: 'Failed to fetch OTs' });
  }
});

// POST /api/telcos/update_status - Update OT status via mock TELCOS API
router.post('/update_status', async (req: Request, res: Response) => {
  try {
    const { otId, status } = req.body;

    if (!otId || !status) {
      res.status(400).json({ error: 'otId and status are required' });
      return;
    }

    const result = await apiService.updateOTStatus(otId, status);
    res.set('X-Mock-Mode', 'true');
    res.json(result);
  } catch (error) {
    logger.error('Error updating OT status', { error });
    res.status(500).json({ error: 'Failed to update OT status' });
  }
});

// GET /api/telcodrive/documents/:otId - Get document status
router.get('/documents/:otId', async (req: Request, res: Response) => {
  try {
    const { otId } = req.params;
    const result = await apiService.getDocumentStatus(otId);
    res.set('X-Mock-Mode', 'true');
    res.json(result);
  } catch (error) {
    logger.error('Error fetching document status', { error });
    res.status(500).json({ error: 'Failed to fetch document status' });
  }
});

export default router;

