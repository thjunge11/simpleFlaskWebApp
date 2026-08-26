#!/bin/sh
set -e

# Reload nginx periodically so certificates renewed by certbot get picked up
nginx -g 'daemon off;' &
NGINX_PID=$!

trap 'kill $NGINX_PID' TERM INT

while :; do
    sleep 12h
    nginx -s reload
done &

wait $NGINX_PID
