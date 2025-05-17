FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Copy the entire project
COPY . .

# Configure Poetry to not create a virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-interaction --no-ansi

# Copy the wait script
COPY docker/wait-for-mongodb.sh /wait-for-mongodb.sh
RUN chmod +x /wait-for-mongodb.sh

# Set environment variables
ENV PYTHONPATH=/app
ENV MONGODB_URI=mongodb://mongodb:27017/
ENV MONGODB_DB=sensor_data

# Run tests
CMD ["poetry", "run", "pytest", "src/data_processing/tests/test_processor.py", "-v"] 
