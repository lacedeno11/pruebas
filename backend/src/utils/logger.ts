type LogLevel = 'info' | 'warn' | 'error' | 'debug';

interface LogEntry {
  timestamp: string;
  level: LogLevel;
  message: string;
  context?: Record<string, any>;
}

class Logger {
  private formatLog(level: LogLevel, message: string, context?: Record<string, any>): LogEntry {
    return {
      timestamp: new Date().toISOString(),
      level,
      message,
      ...(context && { context }),
    };
  }

  private outputLog(entry: LogEntry): void {
    const logString = JSON.stringify(entry);
    
    switch (entry.level) {
      case 'error':
        console.error(logString);
        break;
      case 'warn':
        console.warn(logString);
        break;
      case 'debug':
        console.debug(logString);
        break;
      case 'info':
      default:
        console.log(logString);
        break;
    }
  }

  info(message: string, context?: Record<string, any>): void {
    this.outputLog(this.formatLog('info', message, context));
  }

  warn(message: string, context?: Record<string, any>): void {
    this.outputLog(this.formatLog('warn', message, context));
  }

  error(message: string, context?: Record<string, any>): void {
    this.outputLog(this.formatLog('error', message, context));
  }

  debug(message: string, context?: Record<string, any>): void {
    this.outputLog(this.formatLog('debug', message, context));
  }
}

export const logger = new Logger();
export default logger;

