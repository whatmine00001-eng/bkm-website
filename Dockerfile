# BKM / Timeweb Cloud App Platform: server-side PHP and static site.
# Only approved public build output goes into the production image.
FROM python:3.12-slim AS website-build
WORKDIR /source
COPY . .
RUN BKM_CRM_RELEASE=on BKM_RUNTIME_TARGET=timeweb python3 scripts/build-production.py

FROM php:8.2-apache-bookworm
RUN apt-get update \
    && apt-get install -y --no-install-recommends libcurl4-openssl-dev libonig-dev ca-certificates \
    && docker-php-ext-install curl mbstring \
    && a2enmod headers \
    && rm -rf /var/lib/apt/lists/*
COPY --from=website-build /source/_production_release/ /var/www/html/
COPY timeweb/apache-site.conf /etc/apache2/sites-available/000-default.conf
ENV BKM_HOSTING_TARGET=timeweb
EXPOSE 80
CMD ["apache2-foreground"]
