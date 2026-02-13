import BaseAgent, { AgentResult } from './BaseAgent';
import { logger } from '../utils/logger';

export interface RouterInput {
  message: string;
  eventType?: string;
}

export interface IntentClassification {
  intent: 'ingest_ots' | 'plan_assignment' | 'check_governance' | 'send_notification' | 'unknown';
  confidence: number;
  reasoning: string;
}

export class RouterAgent extends BaseAgent {
  constructor() {
    super('RouterAgent', 'Classifies user input and routes to appropriate agent');
  }

  async execute(input: RouterInput): Promise<AgentResult> {
    try {
      const { message, eventType } = input;

      logger.info('RouterAgent executing', { message, eventType });

      // Use LLM to classify intent
      const classification = await this.classifyIntent(message, eventType);

      logger.info('Intent classified', { classification });

      // Determine next agent based on classified intent
      const nextAgent = this.determineNextAgent(classification.intent);

      return {
        success: true,
        data: {
          intent: classification.intent,
          confidence: classification.confidence,
          reasoning: classification.reasoning,
        },
        llmResponse: JSON.stringify(classification),
        nextAgent,
      };
    } catch (error: any) {
      logger.error('RouterAgent execution failed', { error: error.message });

      return {
        success: false,
        error: `Failed to classify intent: ${error.message}`,
        nextAgent: undefined,
      };
    }
  }

  /**
   * Use LLM to classify the intent of the input message
   */
  private async classifyIntent(
    message: string,
    eventType?: string
  ): Promise<IntentClassification> {
    const systemPrompt = `You are an intent classification agent for a workflow orchestration system.
Your job is to analyze user messages and classify them into one of these intents:

1. ingest_ots: User wants to ingest/import OTs from external APIs (e.g., "ingest new OTs", "import from TELCOS", "load OT data")
2. plan_assignment: User wants to plan and assign OTs to crews (e.g., "plan assignments", "assign OTs", "run planning algorithm")
3. check_governance: User wants to check governance rules and status (e.g., "check governance", "review status", "governance check")
4. send_notification: User wants to send notifications (e.g., "send alert", "notify PM", "send email")
5. unknown: The intent doesn't match any of the above

Return your classification as a JSON object with:
{
  "intent": "one of the above",
  "confidence": 0.0 to 1.0,
  "reasoning": "brief explanation of why you classified it this way"
}

IMPORTANT: Respond ONLY with valid JSON, no additional text.`;

    const userPrompt = `Classify the intent of this message:
Message: "${message}"
${eventType ? `Event Type: "${eventType}"` : ''}

Respond with only a valid JSON object.`;

    try {
      const response = await this.callLLM(userPrompt, systemPrompt);

      // Parse JSON response
      const jsonMatch = response.match(/\{[\s\S]*\}/);
      if (!jsonMatch) {
        throw new Error('Invalid JSON response from LLM');
      }

      const classification = JSON.parse(jsonMatch[0]) as IntentClassification;

      // Validate classification structure
      if (
        !classification.intent ||
        typeof classification.confidence !== 'number' ||
        !classification.reasoning
      ) {
        throw new Error('Invalid classification structure');
      }

      // Ensure confidence is between 0 and 1
      classification.confidence = Math.max(0, Math.min(1, classification.confidence));

      return classification;
    } catch (error: any) {
      logger.warn('LLM classification failed, using fallback', { error: error.message });

      // Fallback: use heuristics if LLM fails
      return this.classifyIntentFallback(message, eventType);
    }
  }

  /**
   * Fallback classification using keyword matching if LLM fails
   */
  private classifyIntentFallback(message: string, eventType?: string): IntentClassification {
    const lowerMessage = message.toLowerCase();

    // Ingest OTs keywords
    if (
      lowerMessage.includes('ingest') ||
      lowerMessage.includes('import') ||
      lowerMessage.includes('load') ||
      lowerMessage.includes('telcos') ||
      lowerMessage.includes('ots from')
    ) {
      return {
        intent: 'ingest_ots',
        confidence: 0.7,
        reasoning: 'Message contains keywords related to OT ingestion',
      };
    }

    // Planning keywords
    if (
      lowerMessage.includes('plan') ||
      lowerMessage.includes('assign') ||
      lowerMessage.includes('planning') ||
      lowerMessage.includes('asigna') ||
      lowerMessage.includes('cuadrilla')
    ) {
      return {
        intent: 'plan_assignment',
        confidence: 0.8,
        reasoning: 'Message contains keywords related to OT planning and assignment',
      };
    }

    // Governance keywords
    if (
      lowerMessage.includes('governance') ||
      lowerMessage.includes('check') ||
      lowerMessage.includes('review') ||
      lowerMessage.includes('status') ||
      lowerMessage.includes('governance check') ||
      lowerMessage.includes('gobernanza')
    ) {
      return {
        intent: 'check_governance',
        confidence: 0.75,
        reasoning: 'Message contains keywords related to governance checks',
      };
    }

    // Notification keywords
    if (
      lowerMessage.includes('notify') ||
      lowerMessage.includes('send') ||
      lowerMessage.includes('alert') ||
      lowerMessage.includes('notification') ||
      lowerMessage.includes('email') ||
      lowerMessage.includes('telegram')
    ) {
      return {
        intent: 'send_notification',
        confidence: 0.7,
        reasoning: 'Message contains keywords related to notifications',
      };
    }

    // If eventType is provided, use it as a hint
    if (eventType) {
      switch (eventType) {
        case 'OT_INGESTION':
          return {
            intent: 'ingest_ots',
            confidence: 0.9,
            reasoning: 'Event type indicates OT ingestion',
          };
        case 'PLANNING':
          return {
            intent: 'plan_assignment',
            confidence: 0.9,
            reasoning: 'Event type indicates planning',
          };
        case 'GOVERNANCE':
          return {
            intent: 'check_governance',
            confidence: 0.9,
            reasoning: 'Event type indicates governance check',
          };
        case 'NOTIFICATION':
          return {
            intent: 'send_notification',
            confidence: 0.9,
            reasoning: 'Event type indicates notification',
          };
      }
    }

    // Default to unknown
    return {
      intent: 'unknown',
      confidence: 0.5,
      reasoning: 'Could not determine intent from message or event type',
    };
  }

  /**
   * Determine which agent should handle the classified intent
   */
  private determineNextAgent(intent: IntentClassification['intent']): string {
    switch (intent) {
      case 'ingest_ots':
        return 'OTSAgent';
      case 'plan_assignment':
        return 'PlanningAgent';
      case 'check_governance':
        return 'GovernanceAgent';
      case 'send_notification':
        return 'CommunicationAgent';
      default:
        return 'CommunicationAgent'; // Default to sending a message if intent unknown
    }
  }
}

export default RouterAgent;

