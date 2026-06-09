FROM python:3.12-slim
WORKDIR /app
COPY packages/studylab_core /app/packages/studylab_core
COPY packages/prompts /app/packages/prompts
COPY services/gateway /app/services/gateway
ENV PYTHONPATH=/app/packages/studylab_core
ENV STUDYLAB_PROMPTS_DIR=/app/packages/prompts
CMD ["python", "-m", "services.gateway.app.main"]
