import cron from 'node-cron';
import { logger } from '../utils/logger';
import { GovernanceAgent } from '../agents/GovernanceAgent';
import { PlanningAgent } from '../agents/PlanningAgent';
import { AgentOrchestrator } from '../agents/AgentOrchestrator';

// Initialize agents
const governanceAgent = new GovernanceAgent();
const planningAgent = new PlanningAgent();

/**
 * Start all governance cron jobs
 * - Daily at midnight: Full governance check
 * - Every 6 hours: PREPLANIFICADA > 48h checks
 * - Daily at 1 AM: Phase 3 nightly optimization
 */
export function startGovernanceCron() {
  logger.info('Initializing governance cron jobs');

  // Job 1: Daily at midnight (00:00) - Full governance check
  const midnightJob = cron.schedule('0 0 * * *', async () => {
    try {
      logger.info('🕐 Running midnight governance check');

      const result = await governanceAgent.execute();

      logger.info('✅ Midnight governance check completed', {
        success: result.success,
        alertsCreated: result.data?.alerts?.length || 0,
      });
    } catch (error: any) {
      logger.error('❌ Midnight governance check failed', {
        error: error.message,
      });
    }
  });

  // Job 2: Every 6 hours - PREPLANIFICADA > 48h checks
  const sixHourlyJob = cron.schedule('0 */6 * * *', async () => {
    try {
      logger.info('⏰ Running 6-hourly PREPLANIFICADA check');

      const result = await governanceAgent.execute();

      logger.info('✅ 6-hourly PREPLANIFICADA check completed', {
        success: result.success,
        highPriorityAlertsCreated: result.data?.alerts?.filter(
          (a: any) => a.alertType === 'HIGH_PRIORITY'
        ).length || 0,
      });
    } catch (error: any) {
      logger.error('❌ 6-hourly PREPLANIFICADA check failed', {
        error: error.message,
      });
    }
  });

  // Job 3: Daily at 1 AM (01:00) - Phase 3 nightly optimization
  const nightlyOptimizationJob = cron.schedule('0 1 * * *', async () => {
    try {
      logger.info('🌙 Running nightly optimization (Phase 3)');

      const result = await planningAgent.execute({ mode: 'phase3' });

      logger.info('✅ Nightly optimization completed', {
        success: result.success,
        optimizedCount: result.data?.results?.phase3?.optimized || 0,
      });
    } catch (error: any) {
      logger.error('❌ Nightly optimization failed', {
        error: error.message,
      });
    }
  });

  logger.info('✨ All governance cron jobs scheduled successfully');

  // Return stop functions for graceful shutdown
  return {
    stopMidnightJob: () => midnightJob.stop(),
    stop6HourlyJob: () => sixHourlyJob.stop(),
    stopNightlyOptimizationJob: () => nightlyOptimizationJob.stop(),
    stopAll: () => {
      midnightJob.stop();
      sixHourlyJob.stop();
      nightlyOptimizationJob.stop();
      logger.info('All governance cron jobs stopped');
    },
  };
}

export default startGovernanceCron;

