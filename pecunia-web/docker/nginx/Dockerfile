# Pecunia Web - Custom Nginx Docker Image
# Multi-stage build for optimized production image

# =============================================================================
# Stage 1: Build custom error pages and prepare assets
# =============================================================================
FROM alpine:3.19 AS builder

RUN apk add --no-cache curl

# Create custom error pages
RUN mkdir -p /tmp/html

# Create 50x error page
RUN cat > /tmp/html/50x.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Service Temporarily Unavailable - Pecunia</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #ffffff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            text-align: center;
            padding: 2rem;
            max-width: 500px;
        }
        .error-code {
            font-size: 6rem;
            font-weight: 700;
            color: #e94560;
            line-height: 1;
            margin-bottom: 1rem;
        }
        h1 {
            font-size: 1.5rem;
            font-weight: 500;
            margin-bottom: 1rem;
            color: #ffffff;
        }
        p {
            color: #a0a0a0;
            margin-bottom: 2rem;
            line-height: 1.6;
        }
        .btn {
            display: inline-block;
            padding: 0.75rem 2rem;
            background: #e94560;
            color: #ffffff;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 500;
            transition: background 0.3s ease;
        }
        .btn:hover {
            background: #ff6b6b;
        }
        .logo {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 2rem;
            color: #e94560;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">Pecunia</div>
        <div class="error-code">503</div>
        <h1>Service Temporarily Unavailable</h1>
        <p>We're performing scheduled maintenance or experiencing high load. Please try again in a few moments.</p>
        <a href="/" class="btn">Try Again</a>
    </div>
</body>
</html>
EOF

# Create maintenance page
RUN cat > /tmp/html/maintenance.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="30">
    <title>Scheduled Maintenance - Pecunia</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #ffffff;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            text-align: center;
            padding: 2rem;
            max-width: 500px;
        }
        .icon {
            font-size: 4rem;
            margin-bottom: 1.5rem;
        }
        h1 {
            font-size: 1.75rem;
            font-weight: 600;
            margin-bottom: 1rem;
        }
        p {
            color: #a0a0a0;
            margin-bottom: 1.5rem;
            line-height: 1.6;
        }
        .progress {
            width: 100%;
            height: 4px;
            background: rgba(255,255,255,0.1);
            border-radius: 2px;
            overflow: hidden;
            margin-bottom: 1rem;
        }
        .progress-bar {
            height: 100%;
            background: #e94560;
            animation: progress 30s linear infinite;
        }
        @keyframes progress {
            0% { width: 0; }
            100% { width: 100%; }
        }
        .note {
            font-size: 0.875rem;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">&#128736;</div>
        <h1>Scheduled Maintenance</h1>
        <p>We're currently performing scheduled maintenance to improve your experience. We'll be back shortly.</p>
        <div class="progress">
            <div class="progress-bar"></div>
        </div>
        <p class="note">This page will automatically refresh.</p>
    </div>
</body>
</html>
EOF

# =============================================================================
# Stage 2: Production Nginx Image
# =============================================================================
FROM nginx:1.25-alpine

# Labels
LABEL maintainer="Pecunia Team <devops@pecunia.com>"
LABEL org.opencontainers.image.title="Pecunia Nginx"
LABEL org.opencontainers.image.description="Production Nginx reverse proxy for Pecunia"
LABEL org.opencontainers.image.version="1.0.0"

# Install required packages
RUN apk add --no-cache \
    curl \
    openssl \
    tzdata \
    && rm -rf /var/cache/apk/*

# Set timezone
ENV TZ=UTC

# Create necessary directories
RUN mkdir -p /app/staticfiles \
    /app/mediafiles \
    /var/www/certbot \
    /etc/nginx/ssl \
    /var/log/nginx \
    /var/cache/nginx \
    && chown -R nginx:nginx /var/cache/nginx \
    && chown -R nginx:nginx /var/log/nginx

# Copy custom error pages from builder
COPY --from=builder /tmp/html/50x.html /usr/share/nginx/html/50x.html
COPY --from=builder /tmp/html/maintenance.html /usr/share/nginx/html/maintenance.html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Generate self-signed SSL certificate for development/initial setup
# In production, replace with real certificates from Let's Encrypt
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/privkey.pem \
    -out /etc/nginx/ssl/fullchain.pem \
    -subj "/C=US/ST=State/L=City/O=Pecunia/CN=localhost" \
    && cp /etc/nginx/ssl/fullchain.pem /etc/nginx/ssl/chain.pem \
    && chmod 600 /etc/nginx/ssl/privkey.pem \
    && chmod 644 /etc/nginx/ssl/fullchain.pem \
    && chmod 644 /etc/nginx/ssl/chain.pem

# Create healthcheck script
RUN cat > /usr/local/bin/healthcheck.sh << 'EOF'
#!/bin/sh
curl -sf http://localhost/nginx-health || exit 1
EOF
RUN chmod +x /usr/local/bin/healthcheck.sh

# Security: Remove default nginx configurations
RUN rm -rf /etc/nginx/conf.d/default.conf \
    /usr/share/nginx/html/index.html

# Create startup script with config validation
RUN cat > /docker-entrypoint.d/99-validate-config.sh << 'EOF'
#!/bin/sh
set -e
echo "Validating Nginx configuration..."
nginx -t
echo "Nginx configuration valid."
EOF
RUN chmod +x /docker-entrypoint.d/99-validate-config.sh

# Expose ports
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

# Run nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
