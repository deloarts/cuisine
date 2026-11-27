# The build stage runs on the builder's own platform: its output is static
# files, the same for every target, so a multi-platform build compiles the
# app once and natively instead of under emulation.
FROM --platform=$BUILDPLATFORM node:22-alpine@sha256:0a7108bf6c7bf5de370ffb1a3ed6be93d405b43ff159f681a8d18c0e2bc2e402 AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL
# build-only skips vue-tsc. Images are built only from commits whose
# frontend job in ci.yml already type-checked them.
RUN npm run build-only

FROM nginx:stable-alpine@sha256:0985e772fb9f729e6fa0980da05fca5d9c468e870eed43071545afa9d2e27d94
COPY --from=build /app/dist /usr/share/nginx/html
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
# Outside conf.d, which nginx includes at http level: nginx.conf includes
# it in the server and in every location that adds a header.
COPY docker/security-headers.conf /etc/nginx/cuisine/security-headers.conf
# The image's entrypoint runs every executable in /docker-entrypoint.d before
# nginx starts; this one writes the trusted proxy list nginx.conf includes.
# The empty file keeps nginx -t working without the entrypoint.
COPY --chmod=0755 docker/trusted-proxies.sh /docker-entrypoint.d/40-cuisine-trusted-proxies.sh
RUN mkdir -p /etc/nginx/cuisine && touch /etc/nginx/cuisine/trusted-proxies.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1
