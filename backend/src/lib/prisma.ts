import { PrismaClient } from '@prisma/client';
import env from '../config/environment';

const globalForPrisma = global as unknown as { prisma: PrismaClient };

export const prisma =
  globalForPrisma.prisma ||
  new PrismaClient({
    log:
      env.SYSTEM_MODE === 'PRODUCTION'
        ? ['error']
        : ['query', 'error', 'warn', 'info'],
  });

if (env.SYSTEM_MODE !== 'PRODUCTION') globalForPrisma.prisma = prisma;

// Graceful shutdown
process.on('SIGINT', async () => {
  console.log('\nReceived SIGINT, disconnecting Prisma...');
  await prisma.$disconnect();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.log('\nReceived SIGTERM, disconnecting Prisma...');
  await prisma.$disconnect();
  process.exit(0);
});

export default prisma;

