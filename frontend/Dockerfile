# Use official Node.js 20 runtime as base image
FROM node:20-alpine

# Set environment variables
# NODE_ENV: Set to development for Vite dev server
# NPM_CONFIG_LOGLEVEL: Reduce npm log verbosity
ENV NODE_ENV=development \
    NPM_CONFIG_LOGLEVEL=warn \
    NPM_CONFIG_PROGRESS=false

# Set working directory inside container
WORKDIR /app

# Install system dependencies
# apk add for Alpine Linux package manager (pre-installed in alpine images)
# No additional system dependencies typically needed for Node.js/React/Vite apps
# But might add git, curl if needed for debugging

# Copy package.json and package-lock.json for dependency installation
# Install from package* glob to support both package.json and package-lock.json
COPY package*.json ./

# Install Node.js dependencies
# Use npm ci (clean install) instead of npm install for reproducible builds
# Also works well in CI/CD and Docker environments
RUN npm ci --prefer-offline --no-audit

# Copy application source code
# Copy only essential source files, not node_modules or dist
COPY src/ ./src/
COPY public/ ./public/
COPY index.html ./
COPY vite.config.js ./
COPY tailwind.config.js ./
COPY postcss.config.js ./

# Create a non-root user for security (optional but recommended)
RUN addgroup -g 1000 appuser && \
    adduser -D -u 1000 -G appuser appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port 5173 for Vite development server
EXPOSE 5173

# Health check for the Vite dev server
# Checks if port 5173 is responding (simple connectivity check)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:5173/ || exit 1

# Default command to run the Vite development server
# Can be overridden when running the container
# --host 0.0.0.0 makes server accessible from outside container
# --port 5173 explicitly sets the port (matches EXPOSE)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

