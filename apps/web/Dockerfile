FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

# dist만 담은 이미지. 시작 시 공유 볼륨(/srv/web)으로 복사하고 종료한다 (Caddy가 서빙)
FROM alpine:3.20
COPY --from=build /app/dist /dist
CMD ["sh", "-c", "rm -rf /srv/web/* && cp -r /dist/. /srv/web/"]
