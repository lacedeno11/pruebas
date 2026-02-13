import { BaseAgent, AgentResult } from './BaseAgent';
import { prisma } from '../lib/prisma';
import { logger } from '../utils/logger';

export interface AgentState {
  currentAgent: string;
  input: any;
  context: Map<string, any>;
  history: Array<{
    agent: string;
    result: AgentResult;
  }>;
}

export class AgentOrchestrator {
  private agents: Map<string, BaseAgent> = new Map();

  /**
   * Register an agent with the orchestrator
   * Agents must implement the BaseAgent interface
   */
  registerAgent(name: string, agent: BaseAgent): void {
    if (this.agents.has(name)) {
      logger.warn(`Agent '${name}' is already registered. Overwriting.`, {
        registeredAgents: Array.from(this.agents.keys()),
      });
    }

    this.agents.set(name, agent);
    logger.info(`Agent '${name}' registered successfully`, {
      totalAgents: this.agents.size,
    });
  }

  /**
   * Get a registered agent by name
   */
  getAgent(name: string): BaseAgent | undefined {
    return this.agents.get(name);
  }

  /**
   * Get all registered agents
   */
  getAllAgents(): Map<string, BaseAgent> {
    return this.agents;
  }

  /**
   * Run a workflow starting from a specific agent
   * Routes between agents based on AgentResult.nextAgent
   * Logs all executions to database
   */
  async runWorkflow(
    initialInput: any,
    startAgent: string
  ): Promise<{ finalResult: any; logs: any[] }> {
    const state: AgentState = {
      currentAgent: startAgent,
      input: initialInput,
      context: new Map(),
      history: [],
    };

    logger.info('Workflow started', {
      startAgent,
      inputSummary: typeof initialInput === 'object'
        ? Object.keys(initialInput).join(', ')
        : String(initialInput).substring(0, 100),
    });

    try {
      // Execute agents in sequence based on routing
      while (state.currentAgent) {
        const agent = this.getAgent(state.currentAgent);

        if (!agent) {
          logger.error(`Agent '${state.currentAgent}' not found`, {
            registeredAgents: Array.from(this.agents.keys()),
          });
          throw new Error(`Agent '${state.currentAgent}' not registered`);
        }

        logger.info(`Executing agent: ${state.currentAgent}`, {
          inputSummary: typeof state.input === 'object'
            ? Object.keys(state.input).join(', ')
            : String(state.input).substring(0, 100),
        });

        // Execute the agent
        const result = await agent.execute(state.input, state.context);

        // Record in history
        state.history.push({
          agent: state.currentAgent,
          result,
        });

        // Log to database
        await this.logAgentExecution(state.currentAgent, result, state.history);

        // Update context and input for next agent
        if (result.data) {
          state.context.set(state.currentAgent, result.data);
        }

        // Route to next agent if specified
        if (result.nextAgent) {
          state.currentAgent = result.nextAgent;
          state.input = result.data || state.input;
        } else {
          // No next agent specified, workflow complete
          state.currentAgent = '';
        }
      }

      // Workflow completed successfully
      const finalResult = state.history.length > 0
        ? state.history[state.history.length - 1].result
        : { success: false, error: 'No agents executed' };

      logger.info('Workflow completed successfully', {
        totalAgentsExecuted: state.history.length,
        finalAgentSuccess: finalResult.success,
      });

      return {
        finalResult,
        logs: state.history,
      };
    } catch (error: any) {
      logger.error('Workflow execution failed', {
        error: error.message,
        currentAgent: state.currentAgent,
        executedAgents: state.history.map((h) => h.agent),
      });

      throw error;
    }
  }

  /**
   * Log agent execution to database
   * Stores agent name, action, result, and any LLM responses for audit trail
   */
  private async logAgentExecution(
    agentName: string,
    result: AgentResult,
    history: AgentState['history']
  ): Promise<void> {
    try {
      // Determine action from agent name and result
      const accion = this.determineAction(agentName, result);

      // Create agent log entry
      await prisma.agentLog.create({
        data: {
          agentName,
          accion,
          resultado: result.success ? 'Success' : 'Failed',
          rawLlmResponse: result.llmResponse
            ? JSON.stringify(result.llmResponse).substring(0, 1000)
            : null,
          errorMessage: result.error || null,
        },
      });

      logger.debug(`Agent execution logged: ${agentName}`, {
        action: accion,
        success: result.success,
      });
    } catch (error: any) {
      logger.error('Failed to log agent execution', {
        agentName,
        error: error.message,
      });
      // Don't throw - logging failure shouldn't stop workflow
    }
  }

  /**
   * Determine action description based on agent and result
   * Used for audit logging
   */
  private determineAction(agentName: string, result: AgentResult): string {
    if (result.error) {
      return `${agentName}_ERROR`;
    }

    switch (agentName) {
      case 'RouterAgent':
        return 'INTENT_CLASSIFICATION';
      case 'OTSAgent':
        return 'OT_INGESTION';
      case 'PlanningAgent':
        return 'PLANNING_EXECUTION';
      case 'GovernanceAgent':
        return 'GOVERNANCE_CHECK';
      case 'CommunicationAgent':
        return 'NOTIFICATION_SENT';
      default:
        return 'AGENT_EXECUTION';
    }
  }

  /**
   * Get execution history for a specific agent from database
   * Used for debugging and monitoring
   */
  async getAgentHistory(
    agentName: string,
    limit: number = 10
  ): Promise<any[]> {
    try {
      const logs = await prisma.agentLog.findMany({
        where: { agentName },
        orderBy: { createdAt: 'desc' },
        take: limit,
      });

      return logs;
    } catch (error: any) {
      logger.error('Failed to fetch agent history', {
        agentName,
        error: error.message,
      });
      return [];
    }
  }

  /**
   * Clear all registered agents (useful for testing)
   */
  clearAgents(): void {
    this.agents.clear();
    logger.info('All agents cleared');
  }

  /**
   * Get orchestrator status
   */
  getStatus(): {
    registeredAgents: string[];
    totalAgents: number;
  } {
    return {
      registeredAgents: Array.from(this.agents.keys()),
      totalAgents: this.agents.size,
    };
  }
}

export default AgentOrchestrator;

