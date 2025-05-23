# Docker Setup Explanation

## Overview
This document explains the Docker setup for the data processing system, including the test, maintenance, and app services, as well as the differences between `docker-compose.yml` and `docker-compose.test.yml`.

---

## Docker Compose Files

### `docker-compose.yml`
This file defines the main services for the application:

- **mongodb:** The MongoDB database service.
  - **Healthcheck:** Ensures the database is ready before other services start.
  - **Environment Variables:** Uses `.env` for credentials.
  - **Volumes:** Persists data in `mongodb_data`.

- **app:** The main application service.
  - **Depends on:** Waits for `mongodb` to be healthy.
  - **Environment Variables:** Uses `.env` for MongoDB connection.
  - **Volumes:** Mounts `./src` and `./data` for live code and data access.
  - **Command:** Runs `python src/load_data.py`.

- **test:** The performance test service.
  - **Depends on:** Waits for `mongodb` to be healthy.
  - **Environment Variables:** Uses `.env` for MongoDB connection.
  - **Volumes:** Mounts `./src` and `./data` for live code and data access.
  - **Command:** Runs `python src/test_performance.py`.
  Unit Tests (test_processor.py):
Data validation
Data type checking
Range validation
Data quality metrics
Database backup functionality
Old data cleanup
Daily data aggregation
MongoDB connection
Performance Test (test_performance.py):
System's ability to handle 500,000 records
Processing speed (records/second)
Memory usage
Data quality metrics
Success rate
Batch processing efficiency

he tests in docker-compose.yml are specifically for performance testing, while the unit tests in test_processor.py are for functional testing. They serve different purposes:
Performance Tests (in docker-compose.yml):
Test system scalability
Measure processing speed
Monitor memory usage
Verify batch processing
Unit Tests (in test_processor.py):
Test individual components
Verify data validation
Check database operations
Ensure data quality

### `docker-compose.test.yml`
This file is used for running tests in isolation:

- **mongodb:** Similar to `docker-compose.yml`, but with a different container name (`sensor_mongodb_test`).
- **test:** Similar to `docker-compose.yml`, but with a different container name (`sensor_test_isolated`).

**Key Differences:**
- **Container Names:** Prevents conflicts with the main services.
- **Isolation:** Ensures tests run in a separate environment from the main app.

---

## Healthcheck
The `healthcheck` in the `mongodb` service ensures that the database is fully operational before other services start. This prevents issues where services might try to connect to a database that isn't ready yet.

---

## Docker for Test, Maintenance, and App

### Test Service
- **Purpose:** Runs performance tests to verify system capability.
- **Setup:** Defined in `docker-compose.yml` and `docker-compose.test.yml`.
- **Command:** `python src/test_performance.py`.

### Maintenance Service
- **Purpose:** Runs maintenance tasks (e.g., checking records).
- **Setup:** Defined in `docker-compose.yml`.
- **Command:** `python src/check_records.py`.

### App Service
- **Purpose:** Runs the main application.
- **Setup:** Defined in `docker-compose.yml`.
- **Command:** `python src/load_data.py`.

---

Having separate files for testing and production ensures:
  - **Isolation:** Tests don't interfere with the main application.
  - **Clarity:** Clear separation of concerns.
  - **Flexibility:** Easy to run tests independently.

---

## Conclusion
The Docker setup is designed to provide a robust, isolated environment for running the application, tests, and maintenance tasks. The use of healthchecks and separate compose files ensures reliability and clarity in the development and testing process. 
