# Environmental Sensor Data Processing System

A high-performance data processing system for environmental sensor data collected by a municipality. The system efficiently processes, validates, and stores sensor data from CSV files with optimized MongoDB operations, parallel processing, and comprehensive performance testing.

## 🛠️ Prerequisites

- Docker
- Docker Compose

## ⚙️ Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd environmental-sensor-system
   ```

2. **Set up environment variables**:
   ```bash
   # rename the example environment file to environment file
   cp .env.example .env
   ```

## 🚀 Running the System

The system uses Docker Compose with different profiles for different purposes:

### 1. **Main Application**
```bash
docker compose --profile app up --build
```
- Starts MongoDB with authentication and optimized settings
- Runs the main data processing application
- Uses the `sensor_data` database

### 2. **Performance Testing**
```bash
docker compose --profile performance-test up --build
```
- Tests the system with 500,000 records ( creates synthetic dataset)
- Uses separate `sensor_data_performance_test` database
- Shows processing speed, memory usage, and quality metrics
- Runs with optimized settings for maximum performance

### 3. **Comprehensive Optimization Testing**
```bash
docker compose --profile comprehensive-test up --build
```
- Tests the system with 500,000 records ( creates synthetic dataset)
- Tests multiple parameter combinations to find optimal configuration
- Evaluates csv reading chunk sizes, validation sizes, worker threads, and connection pools
- Runs each configuration 3 times for statistical reliability
- Uses separate `sensor_data_comprehensive_test` database

### 4. **CSV Reading Performance Testing**
```bash
docker compose --profile csv-test up --build
```
- Tests different CSV reading approaches (sequential, threaded, parallel)
- Compares performance of various I/O strategies
- Uses separate `sensor_data_csv_test` database

### 5. **Index Performance Testing**
```bash
docker compose --profile index-test up --build
```
- Tests whether dropping indexes before inserting data and recreating them is more efficient than keeping indexes during insertion
- Compares performance of indexed vs non-indexed insertion strategies
- Uses separate `sensor_data_index_test` database

### 6. **Stop Services**
```bash
# Stop services but keep data
docker compose down --remove-orphans

# Stop services and remove all data (fresh start)
docker compose down -v --remove-orphans
```

## 📁 Data Structure

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

### Field Descriptions
- `timestamp`: Date and time of the sensor reading
- `device_id`: Unique identifier for the sensor device
- `temperature`: Temperature reading in Celsius (configurable range)
- `humidity`: Humidity percentage (configurable range)
- `pressure`: Atmospheric pressure in hPa (configurable range)
- `light`: Light level reading (configurable minimum)
- `sound`: Sound level reading (configurable minimum)
- `motion`: Motion detection (0 or 1)
- `battery`: Battery level percentage (configurable range)
- `location`: Physical location of the sensor
- `metadata`: Additional processing information

## ⚙️ Configuration

### Environment Variables
All settings are configurable via environment variables:


# Processing Parameters (in settings.py)
CHUNK_SIZE=1000                     # CSV reading chunk size
VALIDATION_CHUNK_SIZE=1000          # Validation parallel chunk size
MONGODB_INSERT_BATCH_SIZE=2000      # MongoDB insert batch size
MAX_WORKERS=4                       # Number of worker threads
MONGODB_POOL_SIZE=5                 # Connection pool minimum
MONGODB_MAX_POOL_SIZE=25            # Connection pool maximum
```
