# Multi-stage build for security service
FROM node:18-alpine AS builder

# Set working directory
WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci --only=production && npm cache clean --force

# Copy source code
COPY . .

# Build TypeScript
RUN npm run build

# Production stage
FROM node:18-alpine AS production

# Install security updates
RUN apk update && apk upgrade

# Create non-root user for security
RUN addgroup -g 1001 -S securityapp && \
    adduser -S securityapp -u 1001

# Set working directory
WORKDIR /app

# Copy built application
COPY --from=builder --chown=securityapp:securityapp /app/dist ./dist
COPY --from=builder --chown=securityapp:securityapp /app/node_modules ./node_modules
COPY --from=builder --chown=securityapp:securityapp /app/package.json ./

# Create directories for logs and models
RUN mkdir -p logs models/anomaly-detection && \
    chown -R securityapp:securityapp /app

# Install additional security tools
RUN apk add --no-cache \
    curl \
    ca-certificates \
    tzdata \
    && rm -rf /var/cache/apk/*

# Set timezone
ENV TZ=UTC

# Security hardening
RUN rm -rf /tmp/* /var/tmp/* && \
    chmod -R 755 /app && \
    chmod -R 644 /app/package.json

# Switch to non-root user
USER securityapp

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8018/health || exit 1

# Expose port
EXPOSE 8018

# Environment variables
ENV NODE_ENV=production
ENV SECURITY_SERVICE_PORT=8018

# Start command
CMD ["node", "dist/index.js"]