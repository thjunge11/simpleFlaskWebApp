FROM nginx:alpine

RUN apk add --no-cache openssl && \
    mkdir -p /etc/nginx/ssl && \
    openssl req -x509 -newkey rsa:4096 \
        -keyout /etc/nginx/ssl/key.pem \
        -out    /etc/nginx/ssl/cert.pem \
        -days   365 -nodes \
        -subj   "/CN=localhost"

COPY nginx.conf /etc/nginx/nginx.conf
