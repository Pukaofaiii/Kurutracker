#!/bin/bash

# ==============================================
# Docker Entrypoint Script for Kurutracker
# ==============================================
# This script runs every time the container starts
# It handles database migrations, static file collection,
# and starting the Django application

set -e  # Exit on error

echo "================================================"
echo " Kurutracker Docker Entrypoint"
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to wait for PostgreSQL
wait_for_postgres() {
    echo -e "${YELLOW}⏳ Waiting for PostgreSQL...${NC}"

    # Use wait-for-it.sh if available
    if [ -f "/wait-for-it.sh" ]; then
        /wait-for-it.sh ${DB_HOST:-db}:${DB_PORT:-5432} --timeout=60 --strict -- echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
    else
        # Fallback: simple loop
        until PGPASSWORD=$DB_PASSWORD psql -h "${DB_HOST:-db}" -U "${DB_USER:-kurutracker_user}" -d "${DB_NAME:-kurutracker}" -c '\q' 2>/dev/null; do
            echo -e "${YELLOW}  PostgreSQL is unavailable - sleeping...${NC}"
            sleep 2
        done
        echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
    fi
}

# Function to wait for Redis
wait_for_redis() {
    echo -e "${YELLOW}⏳ Waiting for Redis...${NC}"

    REDIS_HOST=${CELERY_BROKER_URL##redis://}
    REDIS_HOST=${REDIS_HOST%%/*}
    REDIS_HOST=${REDIS_HOST%%:*}

    until redis-cli -h "${REDIS_HOST:-redis}" ping 2>/dev/null | grep -q PONG; do
        echo -e "${YELLOW}  Redis is unavailable - sleeping...${NC}"
        sleep 2
    done

    echo -e "${GREEN}✓ Redis is ready${NC}"
}

# Wait for services if USE_SQLITE is False
if [ "${USE_SQLITE}" = "False" ] || [ "${USE_SQLITE}" = "false" ]; then
    wait_for_postgres
fi

# Always wait for Redis (for Celery)
if command -v redis-cli >/dev/null 2>&1; then
    wait_for_redis
fi

echo ""
echo "================================================"
echo " Running Django Management Commands"
echo "================================================"

# Apply database migrations
echo -e "${YELLOW}📦 Applying database migrations...${NC}"
python manage.py migrate --noinput
echo -e "${GREEN}✓ Migrations applied${NC}"
echo ""

# Collect static files
echo -e "${YELLOW}🎨 Collecting static files...${NC}"
python manage.py collectstatic --noinput --clear
echo -e "${GREEN}✓ Static files collected${NC}"
echo ""

# Create superuser if needed (only in development)
if [ "${DEBUG}" = "True" ] && [ -n "${DJANGO_SUPERUSER_EMAIL}" ]; then
    echo -e "${YELLOW}👤 Creating superuser (if not exists)...${NC}"
    python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='${DJANGO_SUPERUSER_EMAIL}').exists():
    User.objects.create_superuser(
        email='${DJANGO_SUPERUSER_EMAIL}',
        password='${DJANGO_SUPERUSER_PASSWORD:-admin}'
    )
    print('Superuser created')
else:
    print('Superuser already exists')
END
    echo -e "${GREEN}✓ Superuser check complete${NC}"
    echo ""
fi

# Load initial data (optional)
if [ "${LOAD_INITIAL_DATA}" = "True" ]; then
    echo -e "${YELLOW}📊 Loading initial data...${NC}"
    if [ -f "initial_data.json" ]; then
        python manage.py loaddata initial_data.json
        echo -e "${GREEN}✓ Initial data loaded${NC}"
    else
        echo -e "${YELLOW}⚠ initial_data.json not found, skipping...${NC}"
    fi
    echo ""
fi

echo "================================================"
echo " Starting Application"
echo "================================================"
echo -e "${GREEN}🚀 Executing command: $@${NC}"
echo ""

# Execute the main command
exec "$@"
