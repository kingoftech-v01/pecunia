#!/bin/bash
# Pecunia Web - Wait-for-it Script
# Waits for services (PostgreSQL, Redis) to become available before proceeding
# Usage: ./wait-for-it.sh [options] [-- command args]
#
# Options:
#   -h HOST, --host=HOST       Host to wait for
#   -p PORT, --port=PORT       Port to wait for
#   -t TIMEOUT, --timeout=TIMEOUT
#                              Timeout in seconds (default: 30)
#   -s, --strict               Only execute command if service is available
#   -q, --quiet                Don't output any status messages
#   --postgres                 Wait for PostgreSQL specifically
#   --redis                    Wait for Redis specifically
#   --all                      Wait for all services (postgres + redis)
#   -- command args            Command to execute after service is available

set -e

# =============================================================================
# Default Configuration
# =============================================================================
TIMEOUT=30
STRICT=0
QUIET=0
CHILD_PID=""
HOST=""
PORT=""
WAIT_POSTGRES=0
WAIT_REDIS=0

# Database settings from environment
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-pecunia}"
DB_USER="${DB_USER:-pecunia}"
DB_PASSWORD="${DB_PASSWORD:-}"

# Redis settings from environment
REDIS_URL="${REDIS_URL:-redis://redis:6379/0}"

# =============================================================================
# Output Functions
# =============================================================================
echoerr() {
    if [ "$QUIET" -ne 1 ]; then
        echo "$@" 1>&2
    fi
}

log_info() {
    echoerr "[$(date +'%Y-%m-%d %H:%M:%S')] [INFO] $*"
}

log_error() {
    echoerr "[$(date +'%Y-%m-%d %H:%M:%S')] [ERROR] $*"
}

log_success() {
    echoerr "[$(date +'%Y-%m-%d %H:%M:%S')] [SUCCESS] $*"
}

# =============================================================================
# Usage
# =============================================================================
usage() {
    cat << EOF
Usage: $0 [options] [-- command args]

Wait for services to become available before executing a command.

Options:
    -h HOST, --host=HOST       Host to wait for
    -p PORT, --port=PORT       Port to wait for
    -t TIMEOUT, --timeout=TIMEOUT
                               Timeout in seconds (default: 30)
    -s, --strict               Only execute command if service is available
    -q, --quiet                Don't output status messages
    --postgres                 Wait for PostgreSQL (uses DB_HOST, DB_PORT env vars)
    --redis                    Wait for Redis (uses REDIS_URL env var)
    --all                      Wait for all services (postgres + redis)
    -- command args            Command to execute after services are available

Examples:
    $0 --postgres -- python manage.py migrate
    $0 --all -- gunicorn config.wsgi:application
    $0 -h localhost -p 5432 -t 60 -- echo "PostgreSQL is up"
    $0 --postgres --redis -s -- celery -A config worker

Environment Variables:
    DB_HOST         PostgreSQL host (default: db)
    DB_PORT         PostgreSQL port (default: 5432)
    DB_NAME         PostgreSQL database name (default: pecunia)
    DB_USER         PostgreSQL user (default: pecunia)
    DB_PASSWORD     PostgreSQL password
    REDIS_URL       Redis URL (default: redis://redis:6379/0)
EOF
    exit 1
}

# =============================================================================
# Wait for TCP Port
# =============================================================================
wait_for_tcp() {
    local host=$1
    local port=$2
    local timeout=$3

    log_info "Waiting for ${host}:${port} (timeout: ${timeout}s)..."

    local start_time=$(date +%s)
    while true; do
        # Try to connect using timeout command
        if timeout 1 bash -c "echo > /dev/tcp/${host}/${port}" 2>/dev/null; then
            log_success "${host}:${port} is available!"
            return 0
        fi

        # Alternative: try with nc if available
        if command -v nc &> /dev/null; then
            if nc -z -w1 "$host" "$port" 2>/dev/null; then
                log_success "${host}:${port} is available!"
                return 0
            fi
        fi

        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))

        if [ $elapsed -ge $timeout ]; then
            log_error "Timeout reached waiting for ${host}:${port}"
            return 1
        fi

        sleep 1
    done
}

# =============================================================================
# Wait for PostgreSQL
# =============================================================================
wait_for_postgres() {
    local timeout=$1

    log_info "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."

    local start_time=$(date +%s)
    while true; do
        # Try Python connection
        if python3 -c "
import psycopg
try:
    conn = psycopg.connect(
        host='${DB_HOST}',
        port='${DB_PORT}',
        dbname='${DB_NAME}',
        user='${DB_USER}',
        password='${DB_PASSWORD}',
        connect_timeout=5
    )
    conn.close()
    exit(0)
except Exception:
    exit(1)
" 2>/dev/null; then
            log_success "PostgreSQL is available and accepting connections!"
            return 0
        fi

        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))

        if [ $elapsed -ge $timeout ]; then
            log_error "Timeout reached waiting for PostgreSQL"
            return 1
        fi

        echoerr "PostgreSQL not ready (${elapsed}s elapsed). Retrying..."
        sleep 2
    done
}

# =============================================================================
# Wait for Redis
# =============================================================================
wait_for_redis() {
    local timeout=$1

    log_info "Waiting for Redis at ${REDIS_URL}..."

    local start_time=$(date +%s)
    while true; do
        # Try Python connection
        if python3 -c "
import redis
try:
    r = redis.from_url('${REDIS_URL}', socket_connect_timeout=5)
    r.ping()
    exit(0)
except Exception:
    exit(1)
" 2>/dev/null; then
            log_success "Redis is available and responding to PING!"
            return 0
        fi

        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))

        if [ $elapsed -ge $timeout ]; then
            log_error "Timeout reached waiting for Redis"
            return 1
        fi

        echoerr "Redis not ready (${elapsed}s elapsed). Retrying..."
        sleep 2
    done
}

# =============================================================================
# Parse Arguments
# =============================================================================
parse_arguments() {
    while [ $# -gt 0 ]; do
        case "$1" in
            -h)
                HOST="$2"
                shift 2
                ;;
            --host=*)
                HOST="${1#*=}"
                shift 1
                ;;
            -p)
                PORT="$2"
                shift 2
                ;;
            --port=*)
                PORT="${1#*=}"
                shift 1
                ;;
            -t)
                TIMEOUT="$2"
                shift 2
                ;;
            --timeout=*)
                TIMEOUT="${1#*=}"
                shift 1
                ;;
            -s|--strict)
                STRICT=1
                shift 1
                ;;
            -q|--quiet)
                QUIET=1
                shift 1
                ;;
            --postgres)
                WAIT_POSTGRES=1
                shift 1
                ;;
            --redis)
                WAIT_REDIS=1
                shift 1
                ;;
            --all)
                WAIT_POSTGRES=1
                WAIT_REDIS=1
                shift 1
                ;;
            --help)
                usage
                ;;
            --)
                shift
                CLI_COMMAND=("$@")
                break
                ;;
            *)
                echoerr "Unknown argument: $1"
                usage
                ;;
        esac
    done
}

# =============================================================================
# Signal Handlers
# =============================================================================
cleanup() {
    if [ -n "$CHILD_PID" ] && kill -0 "$CHILD_PID" 2>/dev/null; then
        kill -TERM "$CHILD_PID" 2>/dev/null || true
    fi
    exit 0
}

trap cleanup SIGTERM SIGINT

# =============================================================================
# Main
# =============================================================================
main() {
    parse_arguments "$@"

    local result=0

    # Wait for specific host:port if provided
    if [ -n "$HOST" ] && [ -n "$PORT" ]; then
        wait_for_tcp "$HOST" "$PORT" "$TIMEOUT"
        result=$?
    fi

    # Wait for PostgreSQL if requested
    if [ "$WAIT_POSTGRES" -eq 1 ]; then
        wait_for_postgres "$TIMEOUT"
        result=$?
    fi

    # Wait for Redis if requested
    if [ "$WAIT_REDIS" -eq 1 ]; then
        wait_for_redis "$TIMEOUT"
        result=$?
    fi

    # Check if we have nothing to wait for
    if [ -z "$HOST" ] && [ "$WAIT_POSTGRES" -eq 0 ] && [ "$WAIT_REDIS" -eq 0 ]; then
        log_error "No service specified to wait for"
        usage
    fi

    # Execute command if provided
    if [ ${#CLI_COMMAND[@]} -gt 0 ]; then
        if [ $result -ne 0 ] && [ $STRICT -eq 1 ]; then
            log_error "Strict mode: not executing command due to service unavailability"
            exit $result
        fi

        log_info "Executing command: ${CLI_COMMAND[*]}"
        exec "${CLI_COMMAND[@]}"
    else
        exit $result
    fi
}

main "$@"
