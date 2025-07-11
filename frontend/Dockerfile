# Build stage
FROM node:18-alpine AS build

# Set working directory
WORKDIR /app

# Copy package files
COPY frontend/package*.json ./

# Install dependencies (using npm install since no package-lock.json exists)
RUN npm install

# Copy source code
COPY frontend/ ./

# Set environment variables for build
ARG VITE_API_URL
ARG VITE_PROJECT_ID
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_PROJECT_ID=$VITE_PROJECT_ID

# Build the application
RUN npm run build

# Production stage - run directly with Node.js instead of nginx
FROM node:18-alpine AS production

# Set working directory
WORKDIR /app

# Copy package files
COPY frontend/package*.json ./

# Install all dependencies (including dev dependencies for vite preview)
RUN npm install

# Copy built assets and config from build stage
COPY --from=build /app/dist ./dist
COPY --from=build /app/vite.config.ts ./

# Expose port 3000 to match docker-compose.yml
EXPOSE 3000

# Start the preview server to serve the built files
CMD ["npx", "vite", "preview", "--host", "0.0.0.0", "--port", "3000"] 