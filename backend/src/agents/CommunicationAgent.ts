import BaseAgent, { AgentResult } from './BaseAgent';
import { prisma } from '../lib/prisma';
import { logger } from '../utils/logger';
import env from '../config/environment';
import nodemailer from 'nodemailer';

export interface CommunicationInput {
  type: 'telegram' | 'email';
  recipients: string[];
  subject?: string;
  message: string;
  otIds?: string[];
  alertType?: 'ERROR_GEO' | 'INACTIVIDAD_WARNING' | 'AUTO_CANCELLATION' | 'HIGH_PRIORITY';
}

export class CommunicationAgent extends BaseAgent {
  private emailTransporter: any = null;

  constructor() {
    super('CommunicationAgent', 'Handles sending notifications via Telegram and Email');
    this.initializeEmailTransporter();
  }

  private initializeEmailTransporter() {
    try {
      this.emailTransporter = nodemailer.createTransport({
        host: env.SMTP_HOST,
        port: 587,
        secure: false, // TLS
        auth: {
          user: env.SMTP_USER,
          pass: env.SMTP_PASS,
        },
      });

      logger.info('Email transporter initialized');
    } catch (error: any) {
      logger.warn('Failed to initialize email transporter', { error: error.message });
    }
  }

  async execute(input: CommunicationInput): Promise<AgentResult> {
    try {
      const { type, recipients, subject, message, otIds, alertType } = input;

      logger.info('CommunicationAgent executing', { type, recipientCount: recipients.length, alertType });

      let sent = 0;
      let failed = 0;

      if (type === 'telegram') {
        const result = await this.sendTelegram(recipients, message, otIds, alertType);
        sent = result.sent;
        failed = result.failed;
      } else if (type === 'email') {
        const result = await this.sendEmail(recipients, subject || 'DERCAS PEI Notification', message, otIds, alertType);
        sent = result.sent;
        failed = result.failed;
      } else {
        return {
          success: false,
          error: `Unknown communication type: ${type}`,
        };
      }

      logger.info('CommunicationAgent execution completed', { sent, failed, type });

      // Log communication summary to database
      await prisma.agentLog.create({
        data: {
          agentName: 'CommunicationAgent',
          accion: `${type.toUpperCase()}_NOTIFICATION`,
          resultado: `Sent: ${sent}, Failed: ${failed}`,
          rawLlmResponse: JSON.stringify({
            type,
            recipientCount: recipients.length,
            sent,
            failed,
            alertType,
          }),
        },
      });

      return {
        success: sent > 0,
        data: {
          type,
          sent,
          failed,
          totalAttempted: recipients.length,
        },
        llmResponse: `Notification sent to ${sent} recipient(s). ${failed > 0 ? `${failed} failed.` : 'All successful.'}`,
      };
    } catch (error: any) {
      logger.error('CommunicationAgent execution failed', { error: error.message });

      return {
        success: false,
        error: `CommunicationAgent execution failed: ${error.message}`,
      };
    }
  }

  /**
   * Send Telegram messages
   */
  private async sendTelegram(
    recipients: string[],
    message: string,
    otIds?: string[],
    alertType?: string
  ): Promise<{ sent: number; failed: number }> {
    let sent = 0;
    let failed = 0;

    logger.info('Sending Telegram messages', { recipientCount: recipients.length, alertType });

    for (const recipient of recipients) {
      try {
        // In MOCK mode, just log to console and database
        if (env.SYSTEM_MODE === 'MOCK') {
          logger.info(`[MOCK TELEGRAM] Sent to ${recipient}:`, {
            message: message.substring(0, 100),
            alertType,
            otIds,
          });

          // Log to database
          await prisma.agentLog.create({
            data: {
              agentName: 'CommunicationAgent',
              accion: 'TELEGRAM_SENT',
              resultado: `Telegram message sent to ${recipient}`,
              rawLlmResponse: JSON.stringify({
                recipient,
                message: message.substring(0, 200),
                alertType,
                otIds,
                mode: 'MOCK',
              }),
            },
          });

          sent++;
        } else {
          // In PRODUCTION mode, use actual Telegram API
          const result = await this.sendTelegramProduction(recipient, message, alertType);

          if (result) {
            await prisma.agentLog.create({
              data: {
                agentName: 'CommunicationAgent',
                accion: 'TELEGRAM_SENT',
                resultado: `Telegram message sent to ${recipient}`,
                rawLlmResponse: JSON.stringify({
                  recipient,
                  messageId: result,
                  alertType,
                }),
              },
            });

            sent++;
          } else {
            failed++;
          }
        }
      } catch (error: any) {
        logger.error(`Failed to send Telegram to ${recipient}`, { error: error.message });

        await prisma.agentLog.create({
          data: {
            agentName: 'CommunicationAgent',
            accion: 'TELEGRAM_FAILED',
            resultado: `Failed to send Telegram to ${recipient}`,
            errorMessage: error.message,
          },
        });

        failed++;
      }
    }

    return { sent, failed };
  }

  /**
   * Send production Telegram messages (stubbed for future Telegram API integration)
   */
  private async sendTelegramProduction(recipient: string, message: string, alertType?: string): Promise<string | null> {
    try {
      // TODO: Implement actual Telegram API call using env.TELEGRAM_BOT_TOKEN
      // This is a placeholder for the actual implementation
      logger.info(`[PRODUCTION] Sending Telegram to ${recipient}`, { alertType });

      // Placeholder: return message ID
      return `msg_${Date.now()}`;
    } catch (error: any) {
      logger.error('Telegram API error', { error: error.message });
      return null;
    }
  }

  /**
   * Send Email messages with templates
   */
  private async sendEmail(
    recipients: string[],
    subject: string,
    message: string,
    otIds?: string[],
    alertType?: string
  ): Promise<{ sent: number; failed: number }> {
    let sent = 0;
    let failed = 0;

    logger.info('Sending Email messages', { recipientCount: recipients.length, alertType });

    if (!this.emailTransporter) {
      logger.warn('Email transporter not available');
      return { sent: 0, failed: recipients.length };
    }

    for (const recipient of recipients) {
      try {
        // Generate email body with template
        const emailBody = await this.generateEmailTemplate(message, alertType, otIds);

        // Send email
        const info = await this.emailTransporter.sendMail({
          from: env.SMTP_USER,
          to: recipient,
          subject,
          html: emailBody,
        });

        logger.info(`Email sent to ${recipient}`, {
          messageId: info.messageId,
          alertType,
        });

        // Log to database
        await prisma.agentLog.create({
          data: {
            agentName: 'CommunicationAgent',
            accion: 'EMAIL_SENT',
            resultado: `Email sent to ${recipient}`,
            rawLlmResponse: JSON.stringify({
              recipient,
              messageId: info.messageId,
              alertType,
              otIds,
            }),
          },
        });

        sent++;
      } catch (error: any) {
        logger.error(`Failed to send email to ${recipient}`, { error: error.message });

        await prisma.agentLog.create({
          data: {
            agentName: 'CommunicationAgent',
            accion: 'EMAIL_FAILED',
            resultado: `Failed to send email to ${recipient}`,
            errorMessage: error.message,
          },
        });

        failed++;
      }
    }

    return { sent, failed };
  }

  /**
   * Generate email template based on alert type
   */
  private async generateEmailTemplate(message: string, alertType?: string, otIds?: string[]): Promise<string> {
    let template = `
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #2c3e50; color: white; padding: 20px; border-radius: 5px 5px 0 0; }
        .content { background-color: #ecf0f1; padding: 20px; }
        .footer { background-color: #34495e; color: white; padding: 10px; text-align: center; border-radius: 0 0 5px 5px; }
        .alert { padding: 15px; margin: 10px 0; border-left: 4px solid #e74c3c; background-color: #fadbd8; }
        .success { border-left-color: #27ae60; background-color: #d5f4e6; }
        .warning { border-left-color: #f39c12; background-color: #fef5e7; }
        .info { border-left-color: #3498db; background-color: #d6eaf8; }
        .ot-list { background-color: white; padding: 10px; margin: 10px 0; border-radius: 3px; }
        .ot-item { padding: 5px; border-bottom: 1px solid #bdc3c7; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>DERCAS PEI - Sistema de Gestión Agéntica</h2>
        </div>
        <div class="content">
`;

    // Add alert-specific template
    switch (alertType) {
      case 'ERROR_GEO':
        template += `
            <div class="alert info">
                <h3>⚠️ Error Geográfico en Ingesta de OTs</h3>
                <p>Se detectaron OTs con coordenadas inválidas durante el proceso de ingesta.</p>
                <p><strong>Acción requerida:</strong> Revisar y corregir las coordenadas antes de proceder con la planificación.</p>
            </div>
`;
        break;

      case 'INACTIVIDAD_WARNING':
        template += `
            <div class="alert warning">
                <h3>⚠️ Alerta de Inactividad</h3>
                <p>Se han detectado OTs en estado DETENIDA por un período extendido.</p>
                <p><strong>Acción requerida:</strong> Por favor, revise y actualice el estado de las siguientes OTs.</p>
            </div>
`;
        break;

      case 'AUTO_CANCELLATION':
        template += `
            <div class="alert">
                <h3>🔴 Anulación Automática de OT</h3>
                <p>Una o más OTs han sido automáticamente anuladas debido al tiempo excesivo en estado DETENIDA.</p>
                <p><strong>Próximo paso:</strong> Revisar los registros de anulación y documentar las razones.</p>
            </div>
`;
        break;

      case 'HIGH_PRIORITY':
        template += `
            <div class="alert info">
                <h3>🚨 Alerta de Alta Prioridad</h3>
                <p>Se han detectado OTs esperando planificación por más de 48 horas.</p>
                <p><strong>Acción requerida:</strong> Ejecutar inmediatamente el proceso de planificación.</p>
            </div>
`;
        break;

      default:
        template += `<div class="alert info"><p>${message}</p></div>`;
    }

    // Add OT list if provided
    if (otIds && otIds.length > 0) {
      template += `
            <div class="ot-list">
                <h4>OTs Afectadas:</h4>
`;
      for (const otId of otIds) {
        template += `<div class="ot-item">• ${otId}</div>`;
      }
      template += `
            </div>
`;
    }

    template += `
        </div>
        <div class="footer">
            <p>Este es un mensaje automático del sistema DERCAS PEI. No responda a este correo.</p>
            <p>&copy; 2024 DERCAS PEI. Todos los derechos reservados.</p>
        </div>
    </div>
</body>
</html>
`;

    return template;
  }
}

export default CommunicationAgent;

