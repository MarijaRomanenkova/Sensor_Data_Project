# Environmental Sensor Data Processing System

A data processing system for environmental sensor data collected by a municipality. The system stores and processes data from various sensors measuring environmental metrics like temperature, humidity, smoke, etc.

## Features

- Batch processing of sensor data
- Data validation and quality checks
- MongoDB storage with proper indexing
- Data retention policy (1 year raw data, 5 years aggregated)
- Daily data aggregation
- Automated backups
- Connection pooling for better performance

## Prerequisites

- Python 3.10+
- MongoDB
- Docker (optional)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd environmental-sensor-system
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   Create a `.env` file with:
   ```
   MONGODB_URI=mongodb://admin:password123@mongodb:27017/
   MONGODB_DB=sensor_data
   ```

## Usage

### Loading Data

To load data from CSV files:
```bash
python src/load_data.py
```

### Running Maintenance

To run daily maintenance tasks (aggregation, cleanup, backup):
```bash
python src/maintenance.py
```

### Using Docker

Build and run the maintenance container:
```bash
docker build -f docker/maintenance.Dockerfile -t sensor-maintenance .
docker run --network=host sensor-maintenance
```

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

### Aggregated Data Schema
```json
{
  "timestamp": "ISODate",
  "device_id": "String",
  "location": "String",
  "avg_temperature": "Double",
  "avg_humidity": "Double",
  "avg_pressure": "Double",
  "avg_light": "Double",
  "avg_sound": "Double",
  "avg_motion": "Double",
  "avg_battery": "Double",
  "max_temperature": "Double",
  "min_temperature": "Double",
  "max_humidity": "Double",
  "min_humidity": "Double",
  "max_pressure": "Double",
  "min_pressure": "Double",
  "count": "Integer",
  "metadata": {
    "aggregated_at": "ISODate",
    "period": "String",
    "batch_id": "String"
  }
}
```

## Data Validation

- Temperature: -50°C to 50°C
- Humidity: 0% to 100%
- Pressure: 800 to 1200 hPa
- Light: ≥ 0
- Sound: ≥ 0
- Motion: 0 or 1
- Battery: 0% to 100%

## Maintenance

The system performs the following maintenance tasks daily:
1. Creates daily aggregations by location and device
2. Cleans up old data (raw data > 1 year, aggregated > 5 years)
3. Creates database backups
4. Calculates data quality metrics:
   - Missing data percentage
   - Out-of-range values
   - Device uptime
   - Battery level trends
   - Sensor accuracy metrics


