import { Router, Request, Response } from 'express';
import { prisma } from '../lib/prisma';
import { logger } from '../utils/logger';
import { calculateCentroid } from '../utils/geoUtils';

const router = Router();

// GET /api/cuadrillas - List all crews with optional filters
router.get('/', async (req: Request, res: Response) => {
  try {
    const { type, isActive } = req.query;
    const where: any = {};
    if (type) where.type = type;
    if (isActive !== undefined) where.isActive = isActive === 'true';

    const cuadrillas = await prisma.cuadrilla.findMany({
      where,
      include: {
        ots: true,
        assignments: true,
      },
    });

    const result = cuadrillas.map((c) => ({
      ...c,
      currentLoad: c.ots.length,
      assignedOTsCount: c.ots.length,
    }));

    res.json(result);
  } catch (error) {
    logger.error('Error fetching cuadrillas', { error });
    res.status(500).json({ error: 'Failed to fetch cuadrillas' });
  }
});

// GET /api/cuadrillas/:id - Get single crew with assigned OTs
router.get('/:id', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const cuadrilla = await prisma.cuadrilla.findUnique({
      where: { id },
      include: { ots: true, assignments: true },
    });

    if (!cuadrilla) {
      res.status(404).json({ error: 'Cuadrilla not found' });
      return;
    }

    res.json({
      ...cuadrilla,
      assignedOTsCount: cuadrilla.ots.length,
    });
  } catch (error) {
    logger.error('Error fetching cuadrilla', { error });
    res.status(500).json({ error: 'Failed to fetch cuadrilla' });
  }
});

// POST /api/cuadrillas - Create new crew
router.post('/', async (req: Request, res: Response) => {
  try {
    const { name, type, dailyCapacity } = req.body;

    if (!name || !type) {
      res.status(400).json({ error: 'Name and type are required' });
      return;
    }

    const cuadrilla = await prisma.cuadrilla.create({
      data: {
        name,
        type,
        dailyCapacity: dailyCapacity || 10,
      },
    });

    logger.info(`Cuadrilla created: ${cuadrilla.id}`);
    res.status(201).json(cuadrilla);
  } catch (error) {
    logger.error('Error creating cuadrilla', { error });
    res.status(500).json({ error: 'Failed to create cuadrilla' });
  }
});

// PATCH /api/cuadrillas/:id - Update crew
router.patch('/:id', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const { name, isActive, dailyCapacity } = req.body;

    const cuadrilla = await prisma.cuadrilla.update({
      where: { id },
      data: {
        ...(name !== undefined && { name }),
        ...(isActive !== undefined && { isActive }),
        ...(dailyCapacity !== undefined && { dailyCapacity }),
      },
    });

    res.json(cuadrilla);
  } catch (error) {
    logger.error('Error updating cuadrilla', { error });
    res.status(500).json({ error: 'Failed to update cuadrilla' });
  }
});

// GET /api/cuadrillas/:id/centroid - Calculate and return current centroid
router.get('/:id/centroid', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const cuadrilla = await prisma.cuadrilla.findUnique({
      where: { id },
      include: { ots: true },
    });

    if (!cuadrilla) {
      res.status(404).json({ error: 'Cuadrilla not found' });
      return;
    }

    const validCoords = cuadrilla.ots
      .filter((ot) => ot.lat !== null && ot.long !== null)
      .map((ot) => ({ lat: ot.lat!, long: ot.long! }));

    const centroid = calculateCentroid(validCoords);

    res.json({
      cuadrillaId: id,
      centroid,
      otCount: cuadrilla.ots.length,
      validCoordsCount: validCoords.length,
    });
  } catch (error) {
    logger.error('Error calculating centroid', { error });
    res.status(500).json({ error: 'Failed to calculate centroid' });
  }
});

export default router;

