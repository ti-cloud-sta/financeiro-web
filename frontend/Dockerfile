FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# Caminho base do site: "/" na produção; "/teste/" no ambiente de teste (docker-compose.dev.yml).
ARG BASE_HREF=/
RUN npm run build -- --configuration production --base-href "$BASE_HREF"

FROM nginx:alpine

COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
