#!/bin/bash
# Pecunia Web - Docker Entrypoint Script
# Handles database wait, migrations, static files, and application startup

set -e

# =============================================================================
# Configuration
# =============================================================================
APP_HOME="/app"
SCRIPTS_DIR="${APP_HOME}/scripts"
STATIC_ROOT="${APP_HOME}/staticfiles"
MEDIA_ROOT="${APP_HOME}/mediafiles"
LOG_DIR="${APP_HOME}/logs"

# Database connection settings
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-pecunia}"
DB_USER="${DB_USER:-pecunia}"
DB_MAX_RETRIES="${DB_MAX_RETRIES:-30}"
DB_RETRY_INTERVAL="${DB_RETRY_INTERVAL:-2}"

# Redis connection settings
REDIS_URL="${REDIS_URL:-redis://redis:6379/0}"
REDIS_MAX_RETRIES="${REDIS_MAX_RETRIES:-15}"
REDIS_RETRY_INTERVAL="${REDIS_RETRY_INTERVAL:-2}"

# Application settings
DJANGO_ENV="${DJANGO_ENV:-production}"
RUN_MIGRATIONS="${RUN_MIGRATIONS:-true}"
COLLECT_STATIC="${COLLECT_STATIC:-true}"
CREATE_SUPERUSER="${CREATE_SUPERUSER:-false}"

# =============================================================================
# Logging Functions
# =============================================================================
log_info() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [INFO] $*"
}

log_warn() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [WARN] $*" >&2
}

log_error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [ERROR] $*" >&2
}

log_success() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [SUCCESS] $*"
}

# =============================================================================
# Wait for PostgreSQL
# =============================================================================
wait_for_postgres() {
    log_info "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."

    local retries=0
    while [ $retries -lt $DB_MAX_RETRIES ]; do
        if python -c "
import os
import psycopg
try:
    conn = psycopg.connect(
        host=os.environ.get('DB_HOST', 'db'),
        port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ.get('DB_NAME', 'pecunia'),
        user=os.environ.get('DB_USER', 'pecunia'),
        password=os.environ.get('DB_PASSWORD', ''),
        connect_timeout=5
    )
    conn.close()
    exit(0)
except Exception as e:
    exit(1)
" 2>/dev/null; then
            log_success "PostgreSQL is available!"
            return 0
        fi

        retries=$((retries + 1))
        log_warn "PostgreSQL not ready (attempt ${retries}/${DB_MAX_RETRIES}). Retrying in ${DB_RETRY_INTERVAL}s..."
        sleep $DB_RETRY_INTERVAL
    done

    log_error "Failed to connect to PostgreSQL after ${DB_MAX_RETRIES} attempts"
    return 1
}

# =============================================================================
# Wait for Redis
# =============================================================================
wait_for_redis() {
    log_info "Waiting for Redis..."

    local retries=0
    while [ $retries -lt $REDIS_MAX_RETRIES ]; do
        if python -c "
import os
import redis
try:
    r = redis.from_url(os.environ.get('REDIS_URL', 'redis://redis:6379/0'), socket_connect_timeout=5)
    r.ping()
    exit(0)
except Exception as e:
    exit(1)
" 2>/dev/null; then
            log_success "Redis is available!"
            return 0
        fi

        retries=$((retries + 1))
        log_warn "Redis not ready (attempt ${retries}/${REDIS_MAX_RETRIES}). Retrying in ${REDIS_RETRY_INTERVAL}s..."
        sleep $REDIS_RETRY_INTERVAL
    done

    log_error "Failed to connect to Redis after ${REDIS_MAX_RETRIES} attempts"
    return 1
}

# =============================================================================
# Run Django Migrations
# =============================================================================
run_migrations() {
    if [ "$RUN_MIGRATIONS" = "true" ]; then
        log_info "Running database migrations..."

        # Check for pending migrations
        local pending=$(python manage.py showmigrations --plan 2>/dev/null | grep -c "\[ \]" || echo "0")

        if [ "$pending" -gt 0 ]; then
            log_info "Found ${pending} pending migrations"
            python manage.py migrate --noinput
            log_success "Migrations completed successfully"
        else
            log_info "No pending migrations"
        fi
    else
        log_info "Skipping migrations (RUN_MIGRATIONS=${RUN_MIGRATIONS})"
    fi
}

# =============================================================================
# Collect Static Files
# =============================================================================
collect_static() {
    if [ "$COLLECT_STATIC" = "true" ]; then
        log_info "Collecting static files..."

        # Only collect if there are changes or directory is empty
        if [ ! -d "$STATIC_ROOT" ] || [ -z "$(ls -A $STATIC_ROOT 2>/dev/null)" ]; then
            python manage.py collectstatic --noinput --clear
            log_success "Static files collected"
        else
            # Check if we need to update
            python manage.py collectstatic --noinput --dry-run 2>/dev/null | grep -q "Copying" && {
                python manage.py collectstatic --noinput
                log_success "Static files updated"
            } || {
                log_info "Static files are up to date"
            }
        fi
    else
        log_info "Skipping static file collection (COLLECT_STATIC=${COLLECT_STATIC})"
    fi
}

# =============================================================================
# Create Superuser (if needed)
# =============================================================================
create_superuser() {
    if [ "$CREATE_SUPERUSER" = "true" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
        log_info "Creating superuser..."

        python manage.py shell << 'EOF'
from django.contrib.auth import get_user_model
User = get_user_model()
import os

email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

if email and password:
    if not User.objects.filter(email=email).exists():
        User.objects.create_superuser(
            email=email,
            password=password
        )
        print(f"Superuser {email} created successfully")
    else:
        print(f"Superuser {email} already exists")
else:
    print("DJANGO_SUPERUSER_EMAIL or DJANGO_SUPERUSER_PASSWORD not set")
EOF
    fi
}

# =============================================================================
# Create Required Directories
# =============================================================================
create_directories() {
    log_info "Creating required directories..."

    mkdir -p "$STATIC_ROOT" "$MEDIA_ROOT" "$LOG_DIR"

    # Set permissions if running as root (will be changed to appuser)
    if [ "$(id -u)" = "0" ]; then
        chown -R appuser:appuser "$STATIC_ROOT" "$MEDIA_ROOT" "$LOG_DIR" 2>/dev/null || true
    fi

    log_success "Directories created"
}

# =============================================================================
# Health Check
# =============================================================================
perform_health_check() {
    log_info "Performing startup health check..."

    python -c "
import django
django.setup()

# Check database connection
from django.db import connection
connection.ensure_connection()
print('Database connection: OK')

# Check cache/Redis connection
from django.core.cache import cache
cache.set('health_check', 'ok', 10)
assert cache.get('health_check') == 'ok'
print('Cache connection: OK')

print('Health check passed!')
"

    if [ $? -eq 0 ]; then
        log_success "Health check passed"
        return 0
    else
        log_error "Health check failed"
        return 1
    fi
}

# =============================================================================
# Signal Handlers
# =============================================================================
cleanup() {
    log_info "Received shutdown signal, cleaning up..."
    # Add any cleanup tasks here
    exit 0
}

trap cleanup SIGTERM SIGINT SIGQUIT

# =============================================================================
# Main Entrypoint
# =============================================================================
main() {
    log_info "Starting Pecunia Web (Environment: ${DJANGO_ENV})"
    log_info "Python version: $(python --version)"
    log_info "Django version: $(python -c 'import django; print(django.get_version())')"

    # Create required directories
    create_directories

    # Wait for dependencies
    wait_for_postgres || exit 1
    wait_for_redis || exit 1

    # Run Django setup tasks
    run_migrations
    collect_static
    create_superuser

    # Perform health check
    perform_health_check || {
        log_error "Startup health check failed, exiting..."
        exit 1
    }

    log_success "Initialization complete, starting application..."
    log_info "Executing command: $*"

    # Execute the main command
    exec "$@"
}

# Run main function with all arguments
main "$@"
