# Docker Setup Explanation

## Overview
This document explains the Docker setup for the environmental sensor data processing system, including the main application, test, and maintenance services.

## Docker Compose Configuration

### Main Services (`docker-compose.yml`)

1. **MongoDB Service**
   ```yaml
   mongodb:
     image: mongo:latest
     container_name: sensor_mongodb
     environment:
       - MONGO_INITDB_ROOT_USERNAME=${MONGO_INITDB_ROOT_USERNAME}
       - MONGO_INITDB_ROOT_PASSWORD=${MONGO_INITDB_ROOT_PASSWORD}
     ports:
       - "27017:27017"
     volumes:
       - mongodb_data:/data/db
       - ./docker-entrypoint-initdb.d:/docker-entrypoint-initdb.d:ro
     command: mongod --auth
     healthcheck:
       test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
       interval: 10s
       timeout: 5s
       retries: 5
   ```
   - Uses MongoDB latest version
   - Requires authentication
   - Persists data in `mongodb_data` volume
   - Includes healthcheck to ensure database readiness
   - Exposes port 27017 for external access

2. **Main Application Service**
   ```yaml
   app:
     build:
       context: .
       dockerfile: docker/Dockerfile
     container_name: sensor_app
     depends_on:
       mongodb:
         condition: service_healthy
     environment:
       - MONGODB_URI=${MONGODB_URI}
       - MONGODB_DB=${MONGODB_DB}
     volumes:
       - ./src:/app/src
       - ./data:/app/data
       - ./pyproject.toml:/app/pyproject.toml
       - ./poetry.lock:/app/poetry.lock
     command: python src/load_data.py
   ```
   - Uses custom Dockerfile
   - Waits for MongoDB to be healthy
   - Mounts source code and data directories
   - Uses Poetry for dependency management

3. **Performance Test Service**
   ```yaml
   performance-test:
     build:
       context: .
       dockerfile: docker/Dockerfile
     container_name: sensor_performance_test
     environment:
       - MONGODB_URI=mongodb://${MONGO_INITDB_ROOT_USERNAME}:${MONGO_INITDB_ROOT_PASSWORD}@mongodb:27017/test_sensor_data?authSource=admin
       - MONGODB_DB=test_sensor_data
     volumes:
       - ./src:/app/src
       - ./data:/app/data
       - ./pyproject.toml:/app/pyproject.toml
       - ./poetry.lock:/app/poetry.lock
     command: python src/test_performance.py
     profiles: ["performance-test"]
   ```
   - Uses separate test database
   - Runs performance tests with 500,000 records
   - Measures processing speed and memory usage

4. **Unit/Integration Test Service**
   ```yaml
   test:
     build:
       context: .
       dockerfile: docker/Dockerfile
     container_name: sensor_test
     environment:
       - MONGODB_URI=${MONGODB_URI}
       - MONGODB_DB=${MONGODB_DB}
     volumes:
       - ./src:/app/src
       - ./data:/app/data
       - ./pyproject.toml:/app/pyproject.toml
       - ./poetry.lock:/app/poetry.lock
     command: pytest src/data_processing/tests/ -v
     profiles: ["test"]
   ```
   - Runs unit and integration tests
   - Uses main database for testing
   - Tests data validation, processing, and quality metrics

5. **Maintenance Service**
   ```yaml
   maintenance:
     build:
       context: .
       dockerfile: docker/Dockerfile
     container_name: sensor_maintenance
     environment:
       - MONGODB_URI=${MONGODB_URI}
       - MONGODB_DB=${MONGODB_DB}
     volumes:
       - ./src:/app/src
       - ./data:/app/data
       - ./pyproject.toml:/app/pyproject.toml
       - ./poetry.lock:/app/poetry.lock
     command: python src/maintenance.py
     profiles: ["maintenance"]
   ```
   - Runs daily maintenance tasks
   - Creates daily aggregations
   - Cleans up old data
   - Generates system statistics

### Dockerfile
```dockerfile
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    python3-dev \
    libffi-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s /root/.local/bin/poetry /usr/local/bin/poetry && \
    export PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Configure Poetry
ENV PATH="/root/.local/bin:$PATH"
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-interaction --no-ansi --no-root

# Copy application code
COPY . .

# Install the project
RUN poetry install --no-interaction --no-ansi

# Set environment variables
ENV PYTHONPATH=/app
```
- Uses Python 3.10 slim image
- Installs system dependencies
- Uses Poetry for dependency management
- Configures Python path
- Installs project dependencies

## Running the Services

1. **Start Main Application**:
   ```bash
   docker compose up --build
   ```

2. **Run Unit/Integration Tests**:
   ```bash
   docker compose --profile test up --build
   ```

3. **Run Performance Tests**:
   ```bash
   docker compose --profile performance-test up --build
   ```

4. **Run Maintenance Tasks**:
   ```bash
   docker compose --profile maintenance up --build
   ```

5. **Stop Services**:
   ```bash
   # Keep data
   docker compose down --remove-orphans

   # Remove all data
   docker compose down -v --remove-orphans
   ```

## Environment Variables
Required environment variables in `.env`:
```
MONGO_INITDB_ROOT_USERNAME=admin
MONGO_INITDB_ROOT_PASSWORD=password123
MONGODB_URI=mongodb://admin:password123@mongodb:27017/
MONGODB_DB=sensor_data
```

## Network Configuration
- All services are connected through the `sensor_network` bridge network
- MongoDB is accessible to all services
- Services can communicate using container names as hostnames

## Volume Management
- `mongodb_data`: Persistent storage for MongoDB data
- Source code and data directories are mounted as volumes for live updates
- Poetry dependency files are mounted for consistent dependency management
