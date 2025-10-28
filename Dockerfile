# Multi-stage Dockerfile for Kurutracker Django Application
# Optimized for development with hot reload support

# ============================================
# Stage 1: Base Python Image
# ============================================
FROM python:3.13-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # PostgreSQL client
    libpq-dev \
    postgresql-client \
    # Image processing
    libjpeg-dev \
    zlib1g-dev \
    # Git for django-extensions
    git \
    # Build tools
    gcc \
    g++ \
    make \
    # Networking tools
    curl \
    wget \
    # Node.js for Tailwind (if needed)
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# ============================================
# Stage 2: Dependencies
# ============================================
FROM base as dependencies

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ============================================
# Stage 3: Development
# ============================================
FROM dependencies as development

# Install development tools
RUN pip install \
    ipython \
    django-debug-toolbar \
    watchdog[watchmedo]

# Create non-root user for security
RUN groupadd -r django && \
    useradd -r -g django django && \
    mkdir -p /app/staticfiles /app/media /app/logs && \
    chown -R django:django /app

# Copy entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chown django:django /entrypoint.sh

# Copy wait-for-it script
COPY docker/wait-for-it.sh /wait-for-it.sh
RUN chmod +x /wait-for-it.sh && chown django:django /wait-for-it.sh

# Copy application code
COPY --chown=django:django . .

# Switch to non-root user
USER django

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Run entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default command (development server with hot reload)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
