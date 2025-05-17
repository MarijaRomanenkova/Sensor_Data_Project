# Dataset Documentation

## Dataset Reference
Kaggle. (2024). Simulated IoT Environmental Sensor Dataset. https://www.kaggle.com/datasets/vickykumaryadav/simulated-iot-environmental-sensor-dataset

## Dataset Overview
This dataset contains simulated environmental sensor readings from multiple IoT devices, designed to mimic real-world environmental monitoring data. The data is suitable for testing and developing our municipality's sensor data processing system.

### Data Structure
The dataset includes the following fields:
- `timestamp`: Date and time of the reading (ISO 8601 format)
- `device_id`: Unique identifier for each device (format: 'Device_XX' where XX is a number)
- `temperature`: Temperature readings in Celsius (-50°C to 50°C)
- `humidity`: Humidity measurements in percentage (0% to 100%)
- `pressure`: Atmospheric pressure in hPa (800 to 1200)
- `light`: Light level readings (minimum 0)
- `sound`: Sound level readings (minimum 0)
- `motion`: Motion detection (0 or 1)
- `battery`: Battery level percentage (0% to 100%)
- `location`: Physical location of the sensor (e.g., "Room A")

### Dataset Characteristics
- Total number of records: 100,000
- Time period: 1 year
- Number of devices: 10
- Sampling frequency: 1 hour

### Data Quality
- Missing values: None (simulated dataset)
- Outliers: Present in temperature readings (simulated extreme weather conditions)
- Data format: CSV
- Encoding: UTF-8

### Usage Rights
- License: CC0: Public Domain
- Attribution: Required
- Commercial use: Allowed

## Data Processing Notes
1. Data will be processed in batches of 1000 records
2. Timestamps will be converted to MongoDB's native date format
3. Device IDs will be indexed for efficient querying
4. Data validation will be implemented for:
   - Temperature range: -50°C to 50°C
   - Humidity range: 0% to 100%
   - Pressure range: 800 to 1200 hPa
   - Light: minimum 0
   - Sound: minimum 0
   - Motion: 0 or 1
   - Battery: 0% to 100%

## MongoDB Schema
```json
{
  "sensor_readings": {
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
}
```

## Indexes
1. Primary: `{device_id: 1, timestamp: 1}`
2. Secondary: `{timestamp: 1}`
3. Location: `{location: 1}`
4. Device-Location: `{device_id: 1, location: 1}`

## Data Retention Policy
- Raw data: 1 year
- Aggregated data: 5 years
- Backup frequency: Daily 
