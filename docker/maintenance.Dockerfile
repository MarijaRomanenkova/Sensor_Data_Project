FROM python:3.10-slim

WORKDIR /app

# Install poetry
RUN pip install poetry

# Copy poetry files
COPY pyproject.toml poetry.lock ./

# Configure poetry to not create virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-dev

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
