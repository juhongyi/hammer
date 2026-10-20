FROM node:24.22.0-bookworm-slim

RUN npm install --global pnpm@12.11.2

WORKDIR /workspace

ENV NEXT_TELEMETRY_DISABLED=1 PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile \
    && pnpm exec playwright install --with-deps chromium \
    && rm -rf node_modules /var/lib/apt/lists/*

CMD ["sh", "-ec", "pnpm install --frozen-lockfile && exec pnpm dev"]
