FROM python:3.10-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY .env .

# Create backup directory
RUN mkdir -p /app/backups

# Set environment variables
ENV PYTHONPATH=/app
ENV BACKUP_PATH=/app/backups

# Run maintenance script
CMD ["python", "src/maintenance.py"] 
