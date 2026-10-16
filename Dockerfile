FROM python:3.12-slim
WORKDIR /app
COPY requirements-app.txt .
RUN pip install --no-cache-dir -r requirements-app.txt
COPY api.py .
COPY dashboard/dist ./dashboard/dist
RUN useradd --uid 10001 --create-home appuser
USER appuser
EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
