import BaseAgent, { AgentResult } from './BaseAgent';
import { prisma } from '../lib/prisma';
import { logger } from '../utils/logger';
import { createApiService } from '../services/ApiService';

export interface GovernanceAlert {
  otIds: string[];
  daysDetained?: number;
  alertType: 'INACTIVIDAD_WARNING' | 'AUTO_CANCELLATION' | 'HIGH_PRIORITY';
  severity: 'warning' | 'critical';
  message: string;
}

export class GovernanceAgent extends BaseAgent {
  private apiService = createApiService();

  constructor() {
    super('GovernanceAgent', 'Monitors OT statuses and enforces governance rules');
  }

  async execute(): Promise<AgentResult> {
    try {
      logger.info('GovernanceAgent executing');

      const alerts: GovernanceAlert[] = [];
      let autoCancelled = 0;
      let warningsCreated = 0;

      // Check DETENIDA OTs for time thresholds
      const detainedOTs = await prisma.oT.findMany({
        where: { status: 'DETENIDA' },
      });

      logger.info(`Found ${detainedOTs.length} DETENIDA OTs`);

      for (const ot of detainedOTs) {
        const daysDetained = this.calculateDaysDetained(ot.updatedAt);

        logger.info(`OT ${ot.externalId} detained for ${daysDetained} days`, {
          otId: ot.id,
          updatedAt: ot.updatedAt,
          daysDetained,
        });

        // Day 30: Auto-cancellation
        if (daysDetained >= 30) {
          try {
            // Update OT status to ANULADA
            await prisma.oT.update({
              where: { id: ot.id },
              data: { status: 'ANULADA' },
            });

            // Call MockApiService to simulate external status update
            const mockResult = await this.apiService.updateOTStatus(ot.id, 'ANULADA');

            // Log to AgentLog
            await prisma.agentLog.create({
              data: {
                otId: ot.id,
                agentName: 'GovernanceAgent',
                accion: 'AUTO_CANCELLATION',
                resultado: `Anulada por Governance Agent - Motivo: Exceso de tiempo en estado DETENIDA (${daysDetained} días)`,
                rawLlmResponse: JSON.stringify(mockResult),
              },
            });

            autoCancelled++;

            logger.info(`OT ${ot.externalId} auto-cancelled after ${daysDetained} days`, {
              otId: ot.id,
            });

            // Create alert for communication
            alerts.push({
              otIds: [ot.id],
              daysDetained,
              alertType: 'AUTO_CANCELLATION',
              severity: 'critical',
              message: `OT ${ot.externalId} ha sido anulada por exceso de tiempo en estado DETENIDA (${daysDetained} días).`,
            });
          } catch (error: any) {
            logger.error(`Failed to cancel OT ${ot.externalId}`, { error: error.message });
          }
        }
        // Days 20, 25, 29: Create warning alerts
        else if (daysDetained === 29 || daysDetained === 25 || daysDetained === 20) {
          alerts.push({
            otIds: [ot.id],
            daysDetained,
            alertType: 'INACTIVIDAD_WARNING',
            severity: daysDetained === 29 ? 'critical' : 'warning',
            message: `ALERTA: OT ${ot.externalId} ha estado en estado DETENIDA por ${daysDetained} días. Será anulada en ${30 - daysDetained} día(s).`,
          });

          // Log alert to AgentLog
          await prisma.agentLog.create({
            data: {
              otId: ot.id,
              agentName: 'GovernanceAgent',
              accion: 'INACTIVIDAD_ALERT',
              resultado: `Alerta de inactividad: ${daysDetained} días en estado DETENIDA`,
              rawLlmResponse: JSON.stringify({
                alertType: 'INACTIVIDAD_WARNING',
                daysDetained,
                daysUntilCancellation: 30 - daysDetained,
              }),
            },
          });

          warningsCreated++;

          logger.info(`Alert created for OT ${ot.externalId} (${daysDetained} days detained)`, {
            otId: ot.id,
            daysDetained,
          });
        }
      }

      // Check PREPLANIFICADA OTs for 48h+ inactivity (high priority alerts)
      const preplanOTs = await prisma.oT.findMany({
        where: { status: 'PREPLANIFICADA' },
      });

      logger.info(`Found ${preplanOTs.length} PREPLANIFICADA OTs`);

      const highPriorityOTs: string[] = [];

      for (const ot of preplanOTs) {
        const hoursWaiting = this.calculateHoursWaiting(ot.createdAt);

        if (hoursWaiting > 48) {
          highPriorityOTs.push(ot.id);

          logger.warn(`OT ${ot.externalId} waiting in PREPLANIFICADA for ${hoursWaiting} hours`, {
            otId: ot.id,
            hoursWaiting,
          });
        }
      }

      // If there are high-priority OTs, create alert
      if (highPriorityOTs.length > 0) {
        alerts.push({
          otIds: highPriorityOTs,
          alertType: 'HIGH_PRIORITY',
          severity: 'critical',
          message: `${highPriorityOTs.length} OTs llevan más de 48 horas sin planificar. Requiere atención inmediata.`,
        });

        // Log alert
        await prisma.agentLog.create({
          data: {
            agentName: 'GovernanceAgent',
            accion: 'HIGH_PRIORITY_ALERT',
            resultado: `${highPriorityOTs.length} OTs sin planificar por > 48 horas`,
            rawLlmResponse: JSON.stringify({
              alertType: 'HIGH_PRIORITY',
              otCount: highPriorityOTs.length,
              otIds: highPriorityOTs,
            }),
          },
        });

        logger.info(`High-priority alert created for ${highPriorityOTs.length} OTs`);
      }

      // Log governance execution summary
      await prisma.agentLog.create({
        data: {
          agentName: 'GovernanceAgent',
          accion: 'GOVERNANCE_EXECUTION',
          resultado: `Checked ${detainedOTs.length} DETENIDA OTs, ${preplanOTs.length} PREPLANIFICADA OTs. Auto-cancelled: ${autoCancelled}, Warnings: ${warningsCreated}, Alerts: ${alerts.length}`,
          rawLlmResponse: JSON.stringify({
            detainedOTsChecked: detainedOTs.length,
            preplanOTsChecked: preplanOTs.length,
            autoCancelled,
            warningsCreated,
            alertsCreated: alerts.length,
          }),
        },
      });

      logger.info('GovernanceAgent execution completed', {
        autoCancelled,
        warningsCreated,
        alertsCreated: alerts.length,
      });

      // Route to CommunicationAgent if alerts exist
      const nextAgent = alerts.length > 0 ? 'CommunicationAgent' : undefined;

      return {
        success: true,
        data: {
          alerts,
          autoCancelled,
          warningsCreated,
          detainedOTsChecked: detainedOTs.length,
          preplanOTsChecked: preplanOTs.length,
        },
        llmResponse: JSON.stringify({
          summary: `Governance check completed. Auto-cancelled: ${autoCancelled}, Alerts: ${alerts.length}`,
          alerts,
        }),
        nextAgent,
      };
    } catch (error: any) {
      logger.error('GovernanceAgent execution failed', { error: error.message });

      return {
        success: false,
        error: `GovernanceAgent execution failed: ${error.message}`,
      };
    }
  }

  /**
   * Calculate how many days an OT has been in DETENIDA status
   */
  private calculateDaysDetained(updatedAt: Date): number {
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - updatedAt.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  }

  /**
   * Calculate how many hours an OT has been in PREPLANIFICADA status
   */
  private calculateHoursWaiting(createdAt: Date): number {
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - createdAt.getTime());
    const diffHours = Math.ceil(diffTime / (1000 * 60 * 60));
    return diffHours;
  }
}

export default GovernanceAgent;

