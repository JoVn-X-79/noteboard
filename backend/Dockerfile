# Noteboard backend image
# Base: python:3.11-slim  — minimal footprint
FROM python:3.11-slim

WORKDIR /app

COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ .

EXPOSE 5000

# init_db() is called at startup inside app.py
CMD ["python", "app.py"]
