import { Router, Request, Response } from 'express';
import { prisma } from '../lib/prisma';
import { logger } from '../utils/logger';
import { CreateOTSchema, UpdateOTStatusSchema } from '../utils/validation';
import { createApiService } from '../services/ApiService';

const router = Router();
const apiService = createApiService();

// GET /api/ots - List all OTs with pagination and filters
router.get('/', async (req: Request, res: Response) => {
  try {
    const { status, projectType, page = '1', limit = '20' } = req.query;
    const pageNum = parseInt(page as string, 10);
    const limitNum = parseInt(limit as string, 10);
    const skip = (pageNum - 1) * limitNum;

    const where: any = {};
    if (status) where.status = status;
    if (projectType) where.projectType = projectType;

    const [ots, total] = await Promise.all([
      prisma.oT.findMany({
        where,
        skip,
        take: limitNum,
        include: { cuadrilla: true },
      }),
      prisma.oT.count({ where }),
    ]);

    res.json({
      data: ots,
      pagination: { page: pageNum, limit: limitNum, total },
    });
  } catch (error) {
    logger.error('Error fetching OTs', { error });
    res.status(500).json({ error: 'Failed to fetch OTs' });
  }
});

// GET /api/ots/:id - Get single OT
router.get('/:id', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const ot = await prisma.oT.findUnique({
      where: { id },
      include: { cuadrilla: true, logs: true, assignment: true },
    });

    if (!ot) {
      res.status(404).json({ error: 'OT not found' });
      return;
    }

    res.json(ot);
  } catch (error) {
    logger.error('Error fetching OT', { error });
    res.status(500).json({ error: 'Failed to fetch OT' });
  }
});

// POST /api/ots - Create new OT
router.post('/', async (req: Request, res: Response) => {
  try {
    const validatedData = CreateOTSchema.parse(req.body);

    // Check for duplicate externalId
    const existing = await prisma.oT.findUnique({
      where: { externalId: validatedData.externalId },
    });

    if (existing) {
      res.status(409).json({ error: 'OT with this externalId already exists' });
      return;
    }

    // Check for geo error
    const hasGeoError =
      validatedData.lat === undefined || validatedData.long === undefined;

    const ot = await prisma.oT.create({
      data: {
        ...validatedData,
        hasGeoError,
      },
    });

    if (hasGeoError) {
      logger.warn('OT created with GEO error', { otId: ot.id });
    }

    res.status(201).json(ot);
  } catch (error) {
    logger.error('Error creating OT', { error });
    res.status(400).json({ error: 'Invalid OT data' });
  }
});

// PATCH /api/ots/:id - Update OT fields
router.patch('/:id', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const { clienteName, loginId, lat, long } = req.body;

    const ot = await prisma.oT.update({
      where: { id },
      data: {
        ...(clienteName !== undefined && { clienteName }),
        ...(loginId !== undefined && { loginId }),
        ...(lat !== undefined && { lat }),
        ...(long !== undefined && { long }),
      },
    });

    res.json(ot);
  } catch (error) {
    logger.error('Error updating OT', { error });
    res.status(500).json({ error: 'Failed to update OT' });
  }
});

// PATCH /api/ots/:id/status - Update OT status with business rules
router.patch('/:id/status', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const validatedData = UpdateOTStatusSchema.parse(req.body);

    const ot = await prisma.oT.findUnique({ where: { id } });

    if (!ot) {
      res.status(404).json({ error: 'OT not found' });
      return;
    }

    // Business rule: PUBLICO projects cannot move to FINALIZADA without 29 documents
    if (
      ot.projectType === 'PUBLICO' &&
      validatedData.status === 'FINALIZADA'
    ) {
      const docStatus = await apiService.getDocumentStatus(ot.id);
      if (docStatus.documentCount < 29) {
        res.status(400).json({
          error: `Cannot finalize PUBLICO project without 29 documents. Current: ${docStatus.documentCount}/29`,
        });
        return;
      }
    }

    const updatedOT = await prisma.oT.update({
      where: { id },
      data: { status: validatedData.status },
    });

    // Log status change
    await prisma.agentLog.create({
      data: {
        otId: id,
        agentName: 'Manual Change',
        accion: 'Status Change',
        resultado: `Status changed to ${validatedData.status}`,
        ...(validatedData.reason && { rawLlmResponse: validatedData.reason }),
      },
    });

    logger.info(`OT ${id} status changed to ${validatedData.status}`);
    res.json(updatedOT);
  } catch (error) {
    logger.error('Error updating OT status', { error });
    res.status(500).json({ error: 'Failed to update OT status' });
  }
});

export default router;

