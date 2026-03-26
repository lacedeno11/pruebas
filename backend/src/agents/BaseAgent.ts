import { OpenAI } from 'openai';
import env from '../config/environment';

export interface AgentResult {
  success: boolean;
  data?: any;
  error?: string;
  llmResponse?: string;
  nextAgent?: string;
}

export abstract class BaseAgent {
  protected name: string;
  protected description: string;
  protected llmClient: OpenAI;

  constructor(name: string, description: string) {
    this.name = name;
    this.description = description;
    this.llmClient = new OpenAI({
      apiKey: env.OPENAI_API_KEY,
    });
  }

  /**
   * Abstract method that must be implemented by subclasses
   * Each agent implements its own execution logic
   */
  abstract execute(input: any, context?: any): Promise<AgentResult>;

  /**
   * Protected method to call OpenAI LLM with structured prompts
   * Uses gpt-4 model with temperature 0.7 for balanced reasoning
   */
  protected async callLLM(
    prompt: string,
    systemPrompt?: string
  ): Promise<string> {
    try {
      const messages: OpenAI.Chat.ChatCompletionMessageParam[] = [];

      if (systemPrompt) {
        messages.push({
          role: 'system',
          content: systemPrompt,
        });
      }

      messages.push({
        role: 'user',
        content: prompt,
      });

      const response = await this.llmClient.chat.completions.create({
        model: 'gpt-4',
        temperature: 0.7,
        messages,
      });

      const content = response.choices[0]?.message?.content;
      if (!content) {
        throw new Error('No response content from OpenAI');
      }

      return content;
    } catch (error: any) {
      throw new Error(`LLM call failed: ${error.message}`);
    }
  }

  /**
   * Helper method to get agent name
   */
  getName(): string {
    return this.name;
  }

  /**
   * Helper method to get agent description
   */
  getDescription(): string {
    return this.description;
  }
}

export default BaseAgent;

