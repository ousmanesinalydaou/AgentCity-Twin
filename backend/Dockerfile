FROM python:3.12-slim-bookworm AS dependencies
WORKDIR /build
COPY backend/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /srv/agentcity
COPY --from=dependencies /install /usr/local
COPY backend /srv/agentcity/backend
COPY data /srv/agentcity/data
ENV PYTHONPATH=/srv/agentcity/backend
RUN useradd --no-create-home --system --uid 10001 agentcity
USER agentcity
EXPOSE 8100
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8100"]

