# One image: build the interface, then run the Python service that serves it and the API.
FROM node:22-slim AS ui
WORKDIR /ui
RUN npm install -g pnpm@10
COPY ui/package.json ui/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY ui/ ./
# The hosted build reads the stock table from the server; everything else is still sample data.
ENV VITE_API_MODE=live
RUN pnpm build

FROM python:3.13-slim
RUN pip install --no-cache-dir uv
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
COPY backend/src ./src
RUN uv sync --frozen --no-dev
COPY --from=ui /ui/dist /app/static
ENV STEADY_STATIC_DIR=/app/static
CMD ["sh", "-c", "STEADY_VERSION=${RAILWAY_GIT_COMMIT_SHA:-dev} exec uv run --no-dev uvicorn steady.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
