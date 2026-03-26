import dotenv from 'dotenv';

dotenv.config();

export type SystemMode = 'MOCK' | 'PRODUCTION';

export interface Environment {
  SYSTEM_MODE: SystemMode;
  DATABASE_URL: string;
  OPENAI_API_KEY: string;
  PORT: number;
  TELEGRAM_BOT_TOKEN: string;
  SMTP_HOST: string;
  SMTP_USER: string;
  SMTP_PASS: string;
}

function getRequiredEnvVar(key: string): string {
  const value = process.env[key];
  if (!value) {
    throw new Error(`Missing required environment variable: ${key}`);
  }
  return value;
}

function getOptionalEnvVar(key: string, defaultValue?: string): string {
  const value = process.env[key];
  return value ?? defaultValue ?? '';
}

const SYSTEM_MODE = (process.env.SYSTEM_MODE || 'MOCK') as SystemMode;
const isProduction = SYSTEM_MODE === 'PRODUCTION';

// In PRODUCTION mode, all variables are required
// In MOCK mode, only DATABASE_URL and SYSTEM_MODE are required
const requiredVars = isProduction
  ? [
      'DATABASE_URL',
      'OPENAI_API_KEY',
      'TELEGRAM_BOT_TOKEN',
      'SMTP_HOST',
      'SMTP_USER',
      'SMTP_PASS',
    ]
  : ['DATABASE_URL'];

for (const key of requiredVars) {
  if (!process.env[key]) {
    throw new Error(
      `Missing required environment variable in ${SYSTEM_MODE} mode: ${key}`
    );
  }
}

export const env: Environment = {
  SYSTEM_MODE,
  DATABASE_URL: getRequiredEnvVar('DATABASE_URL'),
  OPENAI_API_KEY: getOptionalEnvVar(
    'OPENAI_API_KEY',
    'sk-mock-key-for-development'
  ),
  PORT: parseInt(process.env.PORT || '3000', 10),
  TELEGRAM_BOT_TOKEN: getOptionalEnvVar('TELEGRAM_BOT_TOKEN', ''),
  SMTP_HOST: getOptionalEnvVar('SMTP_HOST', ''),
  SMTP_USER: getOptionalEnvVar('SMTP_USER', ''),
  SMTP_PASS: getOptionalEnvVar('SMTP_PASS', ''),
};

// Validate PORT is a valid number
if (isNaN(env.PORT) || env.PORT <= 0 || env.PORT > 65535) {
  throw new Error(
    `Invalid PORT: ${process.env.PORT}. Must be a number between 1 and 65535.`
  );
}

export default env;

