# ---- frontend build stage ----
# Frontend statically imports the repo-root config.json (../../../config.json from
# src/lib/api.js), so it needs the same repo-root/frontend sibling layout as a real checkout.
FROM node:22-slim AS frontend-build
WORKDIR /app/frontend
COPY config.json config.v1.json config.v2.json config.v3.json config.v3.1.json /app/
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- backend runtime stage ----
FROM python:3.12-slim AS backend
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY config.json config.v1.json config.v2.json config.v3.json config.v3.1.json ./
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
