#!/bin/sh
# Run this once on the host before starting the stack for the first time
# (or whenever the domain changes) to obtain the initial Let's Encrypt certificate.
# Usage: ./nginx/init-letsencrypt.sh
set -e

DOMAIN="thomasjunge.de"
EMAIL="thomas.junge@web.de"
COMPOSE_FILE="docker-compose.nginx.yaml"

cd "$(dirname "$0")/.."

echo "### Creating a temporary self-signed certificate for $DOMAIN so nginx can start ###"
docker compose -f "$COMPOSE_FILE" run --rm --entrypoint "\
  mkdir -p /etc/letsencrypt/live/$DOMAIN && \
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout /etc/letsencrypt/live/$DOMAIN/privkey.pem \
    -out /etc/letsencrypt/live/$DOMAIN/fullchain.pem \
    -subj '/CN=localhost'" certbot

echo "### Starting nginx ###"
docker compose -f "$COMPOSE_FILE" up -d nginx

echo "### Deleting temporary certificate for $DOMAIN ###"
docker compose -f "$COMPOSE_FILE" run --rm --entrypoint "\
  rm -rf /etc/letsencrypt/live/$DOMAIN && \
  rm -rf /etc/letsencrypt/archive/$DOMAIN && \
  rm -rf /etc/letsencrypt/renewal/$DOMAIN.conf" certbot

echo "### Requesting the real Let's Encrypt certificate for $DOMAIN ###"
docker compose -f "$COMPOSE_FILE" run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    --email $EMAIL -d $DOMAIN \
    --rsa-key-size 4096 --agree-tos --no-eff-email" certbot

echo "### Reloading nginx with the real certificate ###"
docker compose -f "$COMPOSE_FILE" exec nginx nginx -s reload
