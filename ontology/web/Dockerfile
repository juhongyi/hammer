FROM node:24.22.0-bookworm-slim

RUN npm install --global pnpm@12.11.2

WORKDIR /workspace

ENV NEXT_TELEMETRY_DISABLED=1
CMD ["sh", "-c", "pnpm install --frozen-lockfile && exec pnpm dev"]
