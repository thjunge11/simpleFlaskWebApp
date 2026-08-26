#!/bin/sh
set -e

CERT_DIR=/etc/nginx/ssl
CERT_FILE="$CERT_DIR/cert.pem"
KEY_FILE="$CERT_DIR/key.pem"

if [ -z "$SSL_IP" ]; then
    echo "ERROR: SSL_IP environment variable must be set to this server's public IP." >&2
    exit 1
fi

mkdir -p "$CERT_DIR"

# Keep reusing the same cert/key across restarts so clients that already trust it don't need to re-trust it
if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
    echo "### Generating self-signed certificate for IP $SSL_IP ###"
    openssl req -x509 -nodes -newkey rsa:2048 -days 3650 \
        -keyout "$KEY_FILE" -out "$CERT_FILE" \
        -subj "/CN=$SSL_IP" \
        -addext "subjectAltName=IP:$SSL_IP"
else
    echo "### Reusing existing certificate in $CERT_DIR ###"
fi

exec nginx -g 'daemon off;'
