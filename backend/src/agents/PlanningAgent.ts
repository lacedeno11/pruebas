import BaseAgent, { AgentResult } from './BaseAgent';
import { prisma } from '../lib/prisma';
import { logger } from '../utils/logger';
import { calculateDistance, calculateCentroid } from '../utils/geoUtils';

export interface PlanningInput {
  mode?: 'full' | 'phase1' | 'phase2' | 'phase3';
  projectType?: 'PUBLICO' | 'PRIVADO' | 'TERCERIZADO';
}

export interface Phase1Result {
  assigned: number;
  phase: 1;
}

export interface Phase2Result {
  assigned: number;
  rejected: number;
  phase: 2;
}

export interface Phase3Result {
  optimized: number;
  phase: 3;
}

export class PlanningAgent extends BaseAgent {
  constructor() {
    super('PlanningAgent', 'Orchestrates 3-phase OT assignment algorithm for crew optimization');
  }

  async execute(input: PlanningInput): Promise<AgentResult> {
    try {
      const { mode = 'full', projectType } = input;

      logger.info('PlanningAgent executing', { mode, projectType });

      let results: any = {
        phase1: null,
        phase2: null,
        phase3: null,
      };

      // Execute phases based on mode
      if (mode === 'full' || mode === 'phase1') {
        results.phase1 = await this.phase1_initialBalance(projectType);
      }

      if (mode === 'full' || mode === 'phase2') {
        results.phase2 = await this.phase2_proximityAssignment(projectType);
      }

      if (mode === 'full' || mode === 'phase3') {
        results.phase3 = await this.phase3_nightlyOptimization(projectType);
      }

      // Generate summary using LLM
      const summary = await this.generateSummary(results);

      // Log to database
      await prisma.agentLog.create({
        data: {
          agentName: 'PlanningAgent',
          accion: 'PLANNING_EXECUTION',
          resultado: `Mode: ${mode}, Phase1: ${results.phase1?.assigned || 0}, Phase2: ${results.phase2?.assigned || 0}`,
          rawLlmResponse: JSON.stringify(results),
        },
      });

      return {
        success: true,
        data: {
          mode,
          results,
          summary,
        },
        llmResponse: summary,
      };
    } catch (error: any) {
      logger.error('PlanningAgent execution failed', { error: error.message });

      return {
        success: false,
        error: `PlanningAgent execution failed: ${error.message}`,
      };
    }
  }

  /**
   * Phase 1: Initial Balance
   * Distribute 1 OT to each active cuadrilla for fairness
   */
  private async phase1_initialBalance(projectType?: string): Promise<Phase1Result> {
    try {
      logger.info('Phase 1: Initial Balance starting');

      // Fetch active cuadrillas
      const cuadrillas = await prisma.cuadrilla.findMany({
        where: { isActive: true },
      });

      logger.info(`Found ${cuadrillas.length} active cuadrillas`);

      // Fetch PREPLANIFICADA OTs ordered by priority
      const where: any = { status: 'PREPLANIFICADA' };
      if (projectType) {
        where.projectType = projectType;
      }

      const ots = await prisma.oT.findMany({
        where,
        orderBy: [
          { projectType: 'asc' }, // PUBLICO first (A), then PRIVADO (P), then TERCERIZADO (T)
          { createdAt: 'asc' }, // Older OTs first
        ],
      });

      logger.info(`Found ${ots.length} PREPLANIFICADA OTs`);

      let assigned = 0;

      // Assign 1 OT per cuadrilla until all have one or OTs exhausted
      for (let i = 0; i < cuadrillas.length && i < ots.length; i++) {
        const cuadrilla = cuadrillas[i];
        const ot = ots[i];

        try {
          // Update OT with assignment
          await prisma.oT.update({
            where: { id: ot.id },
            data: {
              assignedCuadrillaId: cuadrilla.id,
              status: 'PLANIFICADA',
            },
          });

          // Create assignment record
          await prisma.assignment.create({
            data: {
              otId: ot.id,
              cuadrillaId: cuadrilla.id,
              assignedByAgent: 'PlanningAgent',
              distanceFromCentroid: 0, // Initial assignment has no centroid yet
            },
          });

          // Update cuadrilla current load
          await prisma.cuadrilla.update({
            where: { id: cuadrilla.id },
            data: { currentLoad: { increment: 1 } },
          });

          assigned++;

          logger.info(`Assigned OT ${ot.externalId} to ${cuadrilla.name}`, {
            otId: ot.id,
            cuadrillaId: cuadrilla.id,
          });
        } catch (error: any) {
          logger.error(`Failed to assign OT ${ot.externalId}`, { error: error.message });
        }
      }

      logger.info('Phase 1: Initial Balance completed', { assigned });

      return { assigned, phase: 1 };
    } catch (error: any) {
      logger.error('Phase 1 failed', { error: error.message });
      throw error;
    }
  }

  /**
   * Phase 2: Proximity Assignment
   * Assign remaining OTs based on geographic proximity to crew centroids
   */
  private async phase2_proximityAssignment(projectType?: string): Promise<Phase2Result> {
    try {
      logger.info('Phase 2: Proximity Assignment starting');

      // Fetch active cuadrillas with their assigned OTs
      const cuadrillas = await prisma.cuadrilla.findMany({
        where: { isActive: true },
        include: { ots: true, assignments: true },
      });

      // Fetch remaining PREPLANIFICADA OTs
      const where: any = { status: 'PREPLANIFICADA' };
      if (projectType) {
        where.projectType = projectType;
      }

      const remainingOTs = await prisma.oT.findMany({
        where,
      });

      logger.info(`Found ${remainingOTs.length} remaining PREPLANIFICADA OTs`);

      let assigned = 0;
      let rejected = 0;

      // For each remaining OT, find best crew
      for (const ot of remainingOTs) {
        if (!ot.lat || !ot.long) {
          logger.warn(`OT ${ot.externalId} has no coordinates, skipping`, { otId: ot.id });
          rejected++;
          continue;
        }

        let bestCuadrilla: typeof cuadrillas[0] | null = null;
        let bestDistance = 10; // 10km threshold

        // Find cuadrilla with smallest distance that hasn't reached capacity
        for (const cuadrilla of cuadrillas) {
          if (cuadrilla.currentLoad >= cuadrilla.dailyCapacity) {
            continue; // Skip if at capacity
          }

          // Calculate centroid of assigned OTs
          const assignedOTs = cuadrilla.ots;
          const coords = assignedOTs
            .filter((o) => o.lat && o.long)
            .map((o) => ({ lat: o.lat!, long: o.long! }));

          let centroid = null;
          if (coords.length > 0) {
            centroid = calculateCentroid(coords);
          } else {
            // Use cuadrilla's last known centroid
            if (cuadrilla.lastCentroidLat && cuadrilla.lastCentroidLong) {
              centroid = {
                lat: cuadrilla.lastCentroidLat,
                long: cuadrilla.lastCentroidLong,
              };
            }
          }

          // Calculate distance if centroid exists
          if (centroid) {
            const distance = calculateDistance(
              ot.lat,
              ot.long,
              centroid.lat,
              centroid.long
            );

            // Check if distance is within threshold and better than current best
            if (distance < bestDistance) {
              bestDistance = distance;
              bestCuadrilla = cuadrilla;
            }
          }
        }

        // Assign if found suitable cuadrilla
        if (bestCuadrilla && bestDistance < 10) {
          try {
            await prisma.oT.update({
              where: { id: ot.id },
              data: {
                assignedCuadrillaId: bestCuadrilla.id,
                status: 'PLANIFICADA',
              },
            });

            await prisma.assignment.create({
              data: {
                otId: ot.id,
                cuadrillaId: bestCuadrilla.id,
                assignedByAgent: 'PlanningAgent',
                distanceFromCentroid: bestDistance,
              },
            });

            await prisma.cuadrilla.update({
              where: { id: bestCuadrilla.id },
              data: { currentLoad: { increment: 1 } },
            });

            assigned++;

            logger.info(`Assigned OT ${ot.externalId} to ${bestCuadrilla.name}`, {
              otId: ot.id,
              cuadrillaId: bestCuadrilla.id,
              distance: bestDistance,
            });
          } catch (error: any) {
            logger.error(`Failed to assign OT ${ot.externalId}`, { error: error.message });
            rejected++;
          }
        } else {
          logger.info(`Assignment rejected for OT ${ot.externalId}`, {
            reason: bestDistance >= 10 ? 'distance > 10km' : 'no available crew',
            distance: bestDistance,
          });
          rejected++;
        }
      }

      logger.info('Phase 2: Proximity Assignment completed', { assigned, rejected });

      return { assigned, rejected, phase: 2 };
    } catch (error: any) {
      logger.error('Phase 2 failed', { error: error.message });
      throw error;
    }
  }

  /**
   * Phase 3: Nightly Optimization
   * Optimize routes by recalculating centroids and reassigning if beneficial
   */
  private async phase3_nightlyOptimization(projectType?: string): Promise<Phase3Result> {
    try {
      logger.info('Phase 3: Nightly Optimization starting');

      // Fetch active cuadrillas with their PLANIFICADA OTs
      const cuadrillas = await prisma.cuadrilla.findMany({
        where: { isActive: true },
        include: {
          ots: {
            where: { status: 'PLANIFICADA' },
          },
          assignments: true,
        },
      });

      let optimized = 0;

      // Recalculate centroid for each cuadrilla
      for (const cuadrilla of cuadrillas) {
        if (cuadrilla.ots.length === 0) {
          continue;
        }

        // Calculate optimal centroid from assigned OTs
        const coords = cuadrilla.ots
          .filter((o) => o.lat && o.long)
          .map((o) => ({ lat: o.lat!, long: o.long! }));

        if (coords.length === 0) {
          continue;
        }

        const newCentroid = calculateCentroid(coords);

        // Update cuadrilla centroid
        await prisma.cuadrilla.update({
          where: { id: cuadrilla.id },
          data: {
            lastCentroidLat: newCentroid.lat,
            lastCentroidLong: newCentroid.long,
          },
        });

        logger.info(`Updated centroid for ${cuadrilla.name}`, {
          lat: newCentroid.lat,
          long: newCentroid.long,
          otCount: cuadrilla.ots.length,
        });

        optimized++;
      }

      // Fetch remaining PREPLANIFICADA OTs for potential reassignment
      const where: any = { status: 'PREPLANIFICADA' };
      if (projectType) {
        where.projectType = projectType;
      }

      const unassignedOTs = await prisma.oT.findMany({
        where,
      });

      // Try to assign unassigned OTs to crews with optimized centroids
      for (const ot of unassignedOTs) {
        if (!ot.lat || !ot.long) {
          continue;
        }

        let bestCuadrilla: typeof cuadrillas[0] | null = null;
        let bestDistance = 10;

        for (const cuadrilla of cuadrillas) {
          if (
            cuadrilla.currentLoad >= cuadrilla.dailyCapacity ||
            !cuadrilla.lastCentroidLat ||
            !cuadrilla.lastCentroidLong
          ) {
            continue;
          }

          const distance = calculateDistance(
            ot.lat,
            ot.long,
            cuadrilla.lastCentroidLat,
            cuadrilla.lastCentroidLong
          );

          if (distance < bestDistance) {
            bestDistance = distance;
            bestCuadrilla = cuadrilla;
          }
        }

        // Assign if found suitable cuadrilla
        if (bestCuadrilla && bestDistance < 10) {
          try {
            await prisma.oT.update({
              where: { id: ot.id },
              data: {
                assignedCuadrillaId: bestCuadrilla.id,
                status: 'PLANIFICADA',
              },
            });

            await prisma.assignment.create({
              data: {
                otId: ot.id,
                cuadrillaId: bestCuadrilla.id,
                assignedByAgent: 'PlanningAgent',
                distanceFromCentroid: bestDistance,
              },
            });

            await prisma.cuadrilla.update({
              where: { id: bestCuadrilla.id },
              data: { currentLoad: { increment: 1 } },
            });

            optimized++;
          } catch (error: any) {
            logger.error(`Failed to assign OT ${ot.externalId} in phase 3`, {
              error: error.message,
            });
          }
        }
      }

      logger.info('Phase 3: Nightly Optimization completed', { optimized });

      return { optimized, phase: 3 };
    } catch (error: any) {
      logger.error('Phase 3 failed', { error: error.message });
      throw error;
    }
  }

  /**
   * Generate human-readable summary using LLM
   */
  private async generateSummary(results: any): Promise<string> {
    try {
      const phase1Stats = results.phase1
        ? `Phase 1 (Initial Balance): Assigned ${results.phase1.assigned} OTs`
        : '';
      const phase2Stats = results.phase2
        ? `Phase 2 (Proximity): Assigned ${results.phase2.assigned}, Rejected ${results.phase2.rejected}`
        : '';
      const phase3Stats = results.phase3
        ? `Phase 3 (Optimization): Optimized ${results.phase3.optimized}`
        : '';

      const statsText = [phase1Stats, phase2Stats, phase3Stats].filter(Boolean).join('. ');

      const prompt = `Create a brief, professional summary of OT assignment planning results in Spanish:
${statsText}

Format as a concise paragraph suitable for dashboard display (max 3 sentences).
Focus on key metrics and status.`;

      const summary = await this.callLLM(prompt);
      return summary;
    } catch (error: any) {
      logger.warn('Failed to generate LLM summary, using fallback', { error: error.message });

      const assigned =
        (results.phase1?.assigned || 0) +
        (results.phase2?.assigned || 0) +
        (results.phase3?.optimized || 0);
      return `Planificación completada: ${assigned} OTs asignados, ${results.phase2?.rejected || 0} rechazados.`;
    }
  }
}

export default PlanningAgent;

