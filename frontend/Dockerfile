# ---------- build: gera o dist/ estático ----------
FROM node:22-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Lido pelo vite.config.ts: vira dist/version.json e import.meta.env.VITE_APP_VERSION
ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION
RUN npm run build

# ---------- runtime: nginx servindo o dist/ ----------
FROM nginx:1.31.8-alpine AS runtime

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

ARG APP_VERSION=dev
# TODO: trocar pelo repositório real (liga o pacote do GHCR ao repositório)
LABEL org.opencontainers.image.source="https://github.com/alv4roso4res/adec" \
      org.opencontainers.image.revision=$APP_VERSION

EXPOSE 80
