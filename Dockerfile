# Python 3.10 Base
FROM python:3.10-slim

# Set Environment Variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Set Working Directory
WORKDIR /app

# Install System Dependencies (if any needed, e.g., for building)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy Requirements
COPY requirements.txt .

# Install Python Dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy Application Code
COPY . .

# Ensure vault structure exists (will be created by main.py on start if missing,
# but good to have permissions set correctly if we were copying it)
# Since we ignore vault/ in dockerignore, main.py's init_vault_structure will handle creation.

# Expose Port (Cloud Run defaults to 8080)
EXPOSE 8080

# Start Application
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]

