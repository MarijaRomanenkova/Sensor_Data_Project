# Environmental Sensor Data Processing System

A data processing system for environmental sensor data collected by a municipality. The system stores and processes data from csv file storing various sensors measuring environmental metrics like temperature, humidity etc.

## Features

- Batch processing of sensor data
- Data validation and quality checks
- MongoDB storage with proper indexing
- Connection pooling for better performance
- Error logging and validation


## Prerequisites

- Docker
- Docker Compose

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd environmental-sensor-system
   ```

2. Set up environment variables:
   ```bash
   # Copy the example environment file
   cp .env.example .env
   ```

## Running the System

The system uses Docker Compose with different profiles for different purposes:

1. **Start Main Application and MongoDB**:
   ```bash
   docker compose --profile app up --build
   ```
   This will:
   - Start MongoDB with authentication
   - Start the main application
   - Load data if the database is empty
   - Persist data between restarts

2. **Run Performance Tests**:
   ```bash
   docker compose --profile performance-test up --build
   ```
   This will:
   - Use a separate test database
   - Run performance tests on 500,000 records
   - Show processing speed and memory usage metrics

3. **Stop Services**:
   ```bash
   # Stop services but keep data
   docker compose down --remove-orphans

   # Stop services and remove all data (fresh start)
   docker compose down -v --remove-orphans
   ```

Note: The `-v` flag in `docker compose down` removes all volumes, including the database data. Use it only when you want to start fresh.

## Data Structure

### Raw Data Schema
```json
{
  "timestamp": "ISODate",
  "device_id": "String",
  "temperature": "Double",
  "humidity": "Double",
  "pressure": "Double",
  "light": "Integer",
  "sound": "Integer",
  "motion": "Integer",
  "battery": "Double",
  "location": "String",
  "metadata": {
    "batch_id": "String",
    "processed_at": "ISODate"
  }
}
```

#### Field Descriptions:
- `timestamp`: Date and time of the sensor reading
- `device_id`: Unique identifier for the sensor device
- `temperature`: Temperature reading in Celsius (range: -50 to 50)
- `humidity`: Humidity percentage (range: 0 to 100)
- `pressure`: Atmospheric pressure in hPa (range: 800 to 1200)
- `light`: Light level reading (minimum: 0)
- `sound`: Sound level reading (minimum: 0)
- `motion`: Motion detection (0 or 1)
- `battery`: Battery level percentage (range: 0 to 100)
- `location`: Physical location of the sensor (e.g., "Room A")
- `metadata`: Additional processing information

## Data Validation

- Temperature: -50°C to 50°C
- Humidity: 0% to 100%
- Pressure: 800 to 1200 hPa
- Light: ≥ 0
- Sound: ≥ 0
- Motion: 0 or 1
- Battery: 0% to 100%
