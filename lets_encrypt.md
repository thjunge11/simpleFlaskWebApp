Empfohlener Ansatz: Certbot als eigener Service in Docker Compose

Das Prinzip: Certbot holt/erneuert das Zertifikat via HTTP-Challenge auf Port 80. Nginx nutzt das Zertifikat für HTTPS.

1. nginx.conf anpassen — Certbot braucht eine spezielle Route für die Challenge:

2. Dockerfile — kein self-signed Cert mehr nötig, nginx kommt ohne Zertifikat aus bis certbot eines holt:

3. docker-compose.yaml — certbot Service + gemeinsame Volumes hinzufügen:

Einrichtungsschritte:

1. YOUR_DOMAIN ersetzen in:

nginx.conf — 3 Stellen
docker-compose.yaml — -d YOUR_DOMAIN und --email YOUR_EMAIL
2. Erstes Zertifikat holen — erst mit --dry-run testen, dann ohne:

Edited
Dockerfile
3. App starten:

Edited
docker-compose.yaml+2-0
4. Automatische Erneuerung — Let's Encrypt Certs laufen 90 Tage. Cronjob auf dem Server:

Edited
docker-compose.yaml+2-0
Hinweis: Nginx startet beim ersten up mit Fehler, falls das Zertifikat noch nicht existiert. Starte daher erst certbot, dann nginx — oder nutze ein Init-Script. Alternativ ist nginx-proxy + acme-companion eine fertige All-in-one-Lösung.