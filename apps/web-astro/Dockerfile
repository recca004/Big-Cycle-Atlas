# Big Cycle Atlas web — production image.
# Build context is the REPOSITORY ROOT (npm workspaces need the root
# lockfile and packages/shared). Stage 1 builds Astro's static output;
# stage 2 serves it through nginx, which also proxies /api to the API
# service — the browser only ever talks to the web container.
FROM node:22-alpine AS build
WORKDIR /repo

COPY package.json package-lock.json ./
COPY apps/web-astro/package.json apps/web-astro/
COPY packages/shared packages/shared
# The lockfile references every workspace; install only what the web
# build needs (skips the legacy Next.js workspace).
RUN npm ci --workspace=@big-cycle-atlas/web-astro --workspace=@big-cycle-atlas/shared

COPY apps/web-astro apps/web-astro
# Empty string -> browser calls /api/... same-origin; nginx proxies to the
# api service. Set a full URL only for a separately-hosted API.
ARG PUBLIC_API_URL=""
ENV PUBLIC_API_URL=$PUBLIC_API_URL
RUN npm run build -w apps/web-astro

FROM nginx:1.27-alpine
COPY --from=build /repo/apps/web-astro/dist /usr/share/nginx/html
COPY apps/web-astro/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
