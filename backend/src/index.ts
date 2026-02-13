import express, { Request, Response, NextFunction } from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import env from './config/environment';
import { prisma } from './lib/prisma';
import { logger } from './utils/logger';
import startGovernanceCron from './jobs/governanceCron';

// Import route handlers
import otsRouter from './routes/ots';
import cuadrillasRouter from './routes/cuadrillas';
import telcosMockRouter from './routes/telcosMock';
import agentsRouter from './routes/agents';

// Configure environment
dotenv.config();

// Initialize Express app
const app = express();

// Middleware
app.use(cors());
app.use(express.json());

// Request logging middleware
app.use((req: Request, res: Response, next: NextFunction) => {
  logger.info(`${req.method} ${req.path}`, {
    query: req.query,
    body: req.body,
  });
  next();
});

// Health check endpoint
app.get('/health', (req: Request, res: Response) => {
  res.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    systemMode: env.SYSTEM_MODE,
  });
});

// Mount API routes
app.use('/api/ots', otsRouter);
app.use('/api/cuadrillas', cuadrillasRouter);
app.use('/api/agents', agentsRouter);
app.use('/api/telcos', telcosMockRouter);

// Telcodrive documents endpoint (part of telcos mock)
app.get('/api/telcodrive/documents/:otId', async (req: Request, res: Response) => {
  try {
    const { otId } = req.params;
    const apiService = require('./services/ApiService').default();
    const result = await apiService.getDocumentStatus(otId);
    res.set('X-Mock-Mode', 'true');
    res.json(result);
  } catch (error) {
    logger.error('Error fetching telcodrive documents', { error });
    res.status(500).json({ error: 'Failed to fetch documents' });
  }
});

// 404 handler
app.use((req: Request, res: Response) => {
  res.status(404).json({
    error: 'Not Found',
    path: req.path,
  });
});

// Error handling middleware
app.use((err: any, req: Request, res: Response, next: NextFunction) => {
  logger.error('Unhandled error', {
    message: err.message,
    stack: err.stack,
    path: req.path,
    method: req.method,
  });

  res.status(err.status || 500).json({
    error: err.message || 'Internal Server Error',
    ...(env.SYSTEM_MODE === 'MOCK' && { stack: err.stack }),
  });
});

// Start server
const startServer = async () => {
  try {
    // Test Prisma connection
    await prisma.$queryRaw`SELECT 1`;
    logger.info('Database connection successful');

    // Start listening
    app.listen(env.PORT, () => {
      logger.info(`🚀 Server running at http://localhost:${env.PORT}`, {
        systemMode: env.SYSTEM_MODE,
        environment: {
          PORT: env.PORT,
          SYSTEM_MODE: env.SYSTEM_MODE,
          DATABASE_URL: env.DATABASE_URL.substring(0, 50) + '...',
        },
      });

      // Start governance cron jobs after server is listening
      startGovernanceCron();
    });
  } catch (error) {
    logger.error('Failed to start server', { error });
    process.exit(1);
  }
};

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
  logger.error('Uncaught Exception', { error });
  process.exit(1);
});

// Handle unhandled promise rejections
process.on('unhandledRejection', (reason, promise) => {
  logger.error('Unhandled Rejection', { reason, promise });
  process.exit(1);
});

// Start the server
startServer();

export default app;



