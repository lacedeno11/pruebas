import BaseAgent, { AgentResult } from './BaseAgent';
import { createApiService } from '../services/ApiService';
import { prisma } from '../lib/prisma';
import { logger } from '../utils/logger';

export interface OTSInput {
  source: 'telcos_api' | 'manual';
  data?: any;
}

export interface OTSError {
  otId: string;
  reason: string;
}

// Ecuador geographic bounds
const ECUADOR_BOUNDS = {
  minLat: -5,
  maxLat: 2,
  minLong: -82,
  maxLong: -75,
};

export class OTSAgent extends BaseAgent {
  private apiService = createApiService();

  constructor() {
    super('OTSAgent', 'Handles OT ingestion, coordinate validation, and database registration');
  }

  async execute(input: OTSInput): Promise<AgentResult> {
    try {
      const { source, data } = input;

      logger.info('OTSAgent executing', { source });

      if (source === 'telcos_api') {
        return await this.ingestFromTelcosAPI();
      } else if (source === 'manual') {
        return await this.ingestManual(data);
      } else {
        return {
          success: false,
          error: `Unknown source: ${source}`,
        };
      }
    } catch (error: any) {
      logger.error('OTSAgent execution failed', { error: error.message });

      return {
        success: false,
        error: `OTSAgent execution failed: ${error.message}`,
      };
    }
  }

  /**
   * Ingest OTs from TELCOS API via MockApiService
   */
  private async ingestFromTelcosAPI(): Promise<AgentResult> {
    const created: string[] = [];
    const errors: OTSError[] = [];
    let hasGeoError = false;

    try {
      logger.info('Fetching OTs from TELCOS API');
      const mockOTs = await this.apiService.getOTs();

      logger.info(`Retrieved ${mockOTs.length} OTs from TELCOS API`);

      // Process each OT
      for (const mockOT of mockOTs) {
        try {
          // Validate coordinates
          const coordValidation = this.validateCoordinates(
            mockOT.lat,
            mockOT.long
          );

          if (!coordValidation.valid) {
            hasGeoError = true;
            errors.push({
              otId: mockOT.external_id,
              reason: coordValidation.error!,
            });
            logger.warn('OT coordinate validation failed', {
              otId: mockOT.external_id,
              reason: coordValidation.error,
            });
          }

          // Create OT in database
          const ot = await prisma.oT.create({
            data: {
              externalId: mockOT.external_id,
              status: 'PREPLANIFICADA',
              projectType: mockOT.project_type as 'PUBLICO' | 'PRIVADO' | 'TERCERIZADO',
              clienteName: mockOT.cliente,
              loginId: mockOT.login,
              lat: mockOT.lat,
              long: mockOT.long,
              hasGeoError: !coordValidation.valid,
            },
          });

          created.push(ot.id);

          logger.info('OT created successfully', {
            otId: ot.id,
            externalId: ot.externalId,
            hasGeoError: ot.hasGeoError,
          });

          // Log to AgentLog if geo error
          if (!coordValidation.valid) {
            await prisma.agentLog.create({
              data: {
                otId: ot.id,
                agentName: 'OTSAgent',
                accion: 'COORDINATE_VALIDATION',
                resultado: 'Failed',
                errorMessage: coordValidation.error,
              },
            });
          }
        } catch (error: any) {
          logger.error('Error creating OT', {
            externalId: mockOT.external_id,
            error: error.message,
          });

          errors.push({
            otId: mockOT.external_id,
            reason: `Database error: ${error.message}`,
          });
        }
      }

      // Log summary
      await prisma.agentLog.create({
        data: {
          agentName: 'OTSAgent',
          accion: 'OT_INGESTION',
          resultado: `Ingested ${created.length} OTs, ${errors.length} errors`,
          rawLlmResponse: JSON.stringify({
            created: created.length,
            errors: errors.length,
            hasGeoError,
          }),
        },
      });

      logger.info('TELCOS API ingestion completed', {
        created: created.length,
        errors: errors.length,
        hasGeoError,
      });

      return {
        success: true,
        data: {
          created: created.length,
          errors,
          source: 'telcos_api',
        },
        llmResponse: JSON.stringify({
          created: created.length,
          errors: errors.length,
          hasGeoError,
        }),
        // If geo errors, route to CommunicationAgent for PM notification
        nextAgent: hasGeoError ? 'CommunicationAgent' : undefined,
      };
    } catch (error: any) {
      logger.error('TELCOS API ingestion failed', { error: error.message });

      return {
        success: false,
        error: `TELCOS API ingestion failed: ${error.message}`,
        data: {
          created: created.length,
          errors,
        },
      };
    }
  }

  /**
   * Ingest manually provided OT data
   */
  private async ingestManual(data: any): Promise<AgentResult> {
    const created: string[] = [];
    const errors: OTSError[] = [];
    let hasGeoError = false;

    if (!data || !Array.isArray(data)) {
      return {
        success: false,
        error: 'Manual ingestion requires array of OT data',
      };
    }

    try {
      logger.info('Ingesting OTs from manual data', { count: data.length });

      for (const otData of data) {
        try {
          // Validate required fields
          if (!otData.externalId || !otData.projectType) {
            errors.push({
              otId: otData.externalId || 'unknown',
              reason: 'Missing required fields: externalId, projectType',
            });
            continue;
          }

          // Validate coordinates
          const coordValidation = this.validateCoordinates(
            otData.lat,
            otData.long
          );

          if (!coordValidation.valid) {
            hasGeoError = true;
            errors.push({
              otId: otData.externalId,
              reason: coordValidation.error!,
            });
          }

          // Create OT
          const ot = await prisma.oT.create({
            data: {
              externalId: otData.externalId,
              status: otData.status || 'PREPLANIFICADA',
              projectType: otData.projectType,
              clienteName: otData.clienteName,
              loginId: otData.loginId,
              lat: otData.lat,
              long: otData.long,
              hasGeoError: !coordValidation.valid,
            },
          });

          created.push(ot.id);

          logger.info('Manual OT created', {
            otId: ot.id,
            externalId: ot.externalId,
          });
        } catch (error: any) {
          logger.error('Error creating manual OT', {
            externalId: otData.externalId,
            error: error.message,
          });

          errors.push({
            otId: otData.externalId || 'unknown',
            reason: error.message,
          });
        }
      }

      // Log summary
      await prisma.agentLog.create({
        data: {
          agentName: 'OTSAgent',
          accion: 'OT_INGESTION',
          resultado: `Ingested ${created.length} manual OTs, ${errors.length} errors`,
          rawLlmResponse: JSON.stringify({
            created: created.length,
            errors: errors.length,
            hasGeoError,
          }),
        },
      });

      return {
        success: true,
        data: {
          created: created.length,
          errors,
          source: 'manual',
        },
        llmResponse: JSON.stringify({
          created: created.length,
          errors: errors.length,
          hasGeoError,
        }),
        nextAgent: hasGeoError ? 'CommunicationAgent' : undefined,
      };
    } catch (error: any) {
      logger.error('Manual ingestion failed', { error: error.message });

      return {
        success: false,
        error: `Manual ingestion failed: ${error.message}`,
        data: {
          created: created.length,
          errors,
        },
      };
    }
  }

  /**
   * Validate OT coordinates are within Ecuador bounds
   */
  private validateCoordinates(
    lat: number | null | undefined,
    long: number | null | undefined
  ): { valid: boolean; error?: string } {
    // Check if coordinates are provided
    if (lat === null || lat === undefined || long === null || long === undefined) {
      return {
        valid: false,
        error: 'Missing coordinates (lat/long)',
      };
    }

    // Check if coordinates are numbers
    if (typeof lat !== 'number' || typeof long !== 'number') {
      return {
        valid: false,
        error: 'Invalid coordinate format (must be numbers)',
      };
    }

    // Check Ecuador bounds
    if (
      lat < ECUADOR_BOUNDS.minLat ||
      lat > ECUADOR_BOUNDS.maxLat ||
      long < ECUADOR_BOUNDS.minLong ||
      long > ECUADOR_BOUNDS.maxLong
    ) {
      return {
        valid: false,
        error: `Coordinates outside Ecuador bounds. Lat: ${lat} (${ECUADOR_BOUNDS.minLat} to ${ECUADOR_BOUNDS.maxLat}), Long: ${long} (${ECUADOR_BOUNDS.minLong} to ${ECUADOR_BOUNDS.maxLong})`,
      };
    }

    return { valid: true };
  }
}

export default OTSAgent;

