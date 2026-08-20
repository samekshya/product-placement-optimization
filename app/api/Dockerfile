FROM python:3.12-slim

WORKDIR /app

# Dependencies first so code edits do not invalidate the pip layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The analysis artifacts are mounted read only at this path by docker-compose.
# They are never written to by this service.
ENV PP_ARTIFACTS_DIR=/data/artifacts

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
