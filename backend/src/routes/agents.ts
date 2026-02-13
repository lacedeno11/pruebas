import { Router, Request, Response } from 'express';
import { prisma } from '../lib/prisma';
import { logger } from '../utils/logger';
import { AgentOrchestrator } from '../agents/AgentOrchestrator';
import { RouterAgent } from '../agents/RouterAgent';
import { OTSAgent } from '../agents/OTSAgent';
import { PlanningAgent } from '../agents/PlanningAgent';

const router = Router();

// Initialize orchestrator and agents (singleton pattern)
let orchestrator: AgentOrchestrator | null = null;

function getOrchestrator(): AgentOrchestrator {
  if (!orchestrator) {
    orchestrator = new AgentOrchestrator();

    // Register all agents
    orchestrator.registerAgent('RouterAgent', new RouterAgent());
    orchestrator.registerAgent('OTSAgent', new OTSAgent());
    orchestrator.registerAgent('PlanningAgent', new PlanningAgent());
    // GovernanceAgent and CommunicationAgent will be registered when created

    logger.info('Agent orchestrator initialized with agents');
  }

  return orchestrator;
}

// POST /api/agents/plan - Trigger planning workflow via AgentOrchestrator
router.post('/plan', async (req: Request, res: Response) => {
  try {
    const { mode = 'full', projectType } = req.body;

    logger.info('Planning workflow triggered', { mode, projectType });

    // Get orchestrator and run planning workflow
    const orch = getOrchestrator();
    const planningAgent = orch.getAgent('PlanningAgent');

    if (!planningAgent) {
      res.status(500).json({ error: 'PlanningAgent not registered' });
      return;
    }

    // Execute planning agent directly (not through orchestrator for this endpoint)
    const result = await planningAgent.execute({ mode: mode as any, projectType });

    // Log execution
    logger.info('Planning workflow completed', {
      success: result.success,
      mode,
    });

    res.json({
      status: result.success ? 'completed' : 'failed',
      mode,
      results: result.data,
      summary: result.llmResponse,
      error: result.error,
    });
  } catch (error: any) {
    logger.error('Error triggering planning agent', { error: error.message });
    res.status(500).json({ error: 'Failed to trigger planning', details: error.message });
  }
});

// POST /api/agents/route - Test router agent with message routing
router.post('/route', async (req: Request, res: Response) => {
  try {
    const { message, eventType } = req.body;

    if (!message) {
      res.status(400).json({ error: 'Message is required' });
      return;
    }

    logger.info('Router workflow triggered', { message, eventType });

    // Get orchestrator and run routing workflow
    const orch = getOrchestrator();

    // Run workflow starting from RouterAgent
    const { finalResult, logs } = await orch.runWorkflow(
      { message, eventType },
      'RouterAgent'
    );

    logger.info('Router workflow completed', {
      intent: finalResult.data?.intent,
      nextAgent: finalResult.nextAgent,
    });

    res.json({
      status: finalResult.success ? 'completed' : 'failed',
      classification: {
        intent: finalResult.data?.intent,
        confidence: finalResult.data?.confidence,
        reasoning: finalResult.data?.reasoning,
      },
      nextAgent: finalResult.nextAgent,
      message: finalResult.llmResponse || finalResult.error,
      executionLogs: logs.map((log) => ({
        agent: log.agent,
        success: log.result.success,
        nextAgent: log.result.nextAgent,
      })),
      error: finalResult.error,
    });
  } catch (error: any) {
    logger.error('Error triggering router agent', { error: error.message });
    res.status(500).json({ error: 'Failed to route message', details: error.message });
  }
});

// GET /api/agents/logs - Get agent execution history with pagination
router.get('/logs', async (req: Request, res: Response) => {
  try {
    const { page = '1', limit = '20', agentName } = req.query;
    const pageNum = parseInt(page as string, 10);
    const limitNum = parseInt(limit as string, 10);
    const skip = (pageNum - 1) * limitNum;

    // Build where clause
    const where: any = {};
    if (agentName) {
      where.agentName = agentName;
    }

    const [logs, total] = await Promise.all([
      prisma.agentLog.findMany({
        where,
        skip,
        take: limitNum,
        orderBy: { createdAt: 'desc' },
        include: { ot: true },
      }),
      prisma.agentLog.count({ where }),
    ]);

    logger.info('Agent logs retrieved', { pageNum, limitNum, total });

    res.json({
      data: logs,
      pagination: {
        page: pageNum,
        limit: limitNum,
        total,
        pages: Math.ceil(total / limitNum),
      },
    });
  } catch (error: any) {
    logger.error('Error fetching agent logs', { error: error.message });
    res.status(500).json({ error: 'Failed to fetch agent logs', details: error.message });
  }
});

// GET /api/agents/status - Get orchestrator status (registered agents)
router.get('/status', async (req: Request, res: Response) => {
  try {
    const orch = getOrchestrator();
    const status = orch.getStatus();

    res.json({
      orchestrator: 'active',
      ...status,
    });
  } catch (error: any) {
    logger.error('Error fetching orchestrator status', { error: error.message });
    res.status(500).json({ error: 'Failed to fetch status' });
  }
});

export default router;


