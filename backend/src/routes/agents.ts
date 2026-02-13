import { Router, Request, Response } from 'express';
import { prisma } from '../lib/prisma';
import { logger } from '../utils/logger';

const router = Router();

// POST /api/agents/plan - Trigger planning workflow
router.post('/plan', async (req: Request, res: Response) => {
  try {
    const { mode = 'full', projectType } = req.body;

    // Placeholder for agent orchestration
    // Will be implemented when AgentOrchestrator is ready
    logger.info('Planning agent triggered', { mode, projectType });

    res.json({
      status: 'planning_initiated',
      mode,
      message: 'Planning workflow started. Check logs for details.',
    });
  } catch (error) {
    logger.error('Error triggering planning agent', { error });
    res.status(500).json({ error: 'Failed to trigger planning' });
  }
});

// POST /api/agents/route - Test router agent
router.post('/route', async (req: Request, res: Response) => {
  try {
    const { message } = req.body;

    if (!message) {
      res.status(400).json({ error: 'Message is required' });
      return;
    }

    // Placeholder for router agent
    logger.info('Router agent triggered', { message });

    res.json({
      status: 'routing_initiated',
      message: `Processing: "${message}"`,
      intent: 'pending', // Will be classified by LLM
    });
  } catch (error) {
    logger.error('Error triggering router agent', { error });
    res.status(500).json({ error: 'Failed to route message' });
  }
});

// GET /api/agents/logs - Get agent execution history
router.get('/logs', async (req: Request, res: Response) => {
  try {
    const { page = '1', limit = '20' } = req.query;
    const pageNum = parseInt(page as string, 10);
    const limitNum = parseInt(limit as string, 10);
    const skip = (pageNum - 1) * limitNum;

    const [logs, total] = await Promise.all([
      prisma.agentLog.findMany({
        skip,
        take: limitNum,
        orderBy: { createdAt: 'desc' },
        include: { ot: true },
      }),
      prisma.agentLog.count(),
    ]);

    res.json({
      data: logs,
      pagination: { page: pageNum, limit: limitNum, total },
    });
  } catch (error) {
    logger.error('Error fetching agent logs', { error });
    res.status(500).json({ error: 'Failed to fetch agent logs' });
  }
});

export default router;

