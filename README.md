# Environmental Sensor Data Processing System

A high-performance data processing system for environmental sensor data collected by a municipality. The system efficiently processes, validates, and stores sensor data from CSV files with optimized MongoDB operations, parallel processing, and comprehensive performance testing.

## 🚀 Features

- **High-Performance Processing**: Optimized pipeline with configurable chunk sizes and parallel processing
- **Data Validation**: Basic validation with configurable ranges for all sensor metrics
- **MongoDB Storage**: Optimized with proper indexing, connection pooling, and schema validation
- **Parallel Processing**: Multi-threaded validation and database insertion
- **Performance Testing**: Comprehensive optimization tests to find optimal configurations
- **Error Handling**: Detailed error logging and validation reporting
- **Environment Configuration**: Fully configurable via environment variables
- **Memory Monitoring**: Real-time memory usage tracking during processing

## 📊 Performance

The system has been optimized through comprehensive testing and achieves:
- **Processing Speed**: ~24,000 records/second with optimal settings
- **Memory Efficiency**: Minimal memory footprint with optimized chunk processing
- **Scalability**: Configurable worker threads and connection pools
- **Reliability**: 100% success rate with proper error handling

### Optimal Configuration (Found through testing):
- **Chunk Size**: 10,000 records
- **Validation Chunk Size**: 1,000 records  
- **MongoDB Insert Batch Size**: 2,000 records
- **Worker Threads**: 8
- **Connection Pool**: 5-25 connections

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
- Tests the system with 500,000 records
- Uses separate `sensor_data_performance_test` database
- Shows processing speed, memory usage, and quality metrics
- Runs with optimized settings for maximum performance

### 3. **Comprehensive Optimization Testing**
```bash
docker compose --profile comprehensive-test up --build
```
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
CHUNK_SIZE=10000                    # CSV reading chunk size
VALIDATION_CHUNK_SIZE=1000          # Validation parallel chunk size
MONGODB_INSERT_BATCH_SIZE=2000      # MongoDB insert batch size
MAX_WORKERS=8                       # Number of worker threads
MONGODB_POOL_SIZE=5                 # Connection pool minimum
MONGODB_MAX_POOL_SIZE=25            # Connection pool maximum
```

### Data Validation Ranges
All validation ranges are configurable in `src/config/settings.py`:

```python
TEMPERATURE_RANGE = (-50, 50)       # Celsius
HUMIDITY_RANGE = (0, 100)           # Percentage
PRESSURE_RANGE = (800, 1200)        # hPa
LIGHT_RANGE = (0, None)             # Minimum 0, no maximum
SOUND_RANGE = (0, None)             # Minimum 0, no maximum
MOTION_RANGE = (0, 1)               # Binary
BATTERY_RANGE = (0, 100)            # Percentage
```

## 🔍 Data Validation

The system performs validation on all incoming data:

- **Field Validation**: Ensures all required fields are present
- **Range Validation**: Validates values against configurable ranges
- **Type Validation**: Ensures correct data types
- **Schema Validation**: MongoDB schema enforcement
- **Error Logging**: Detailed error reporting and statistics

## 📈 Performance Optimization

The system has been extensively optimized through:

1. **Comprehensive Testing**: Multiple parameter combinations tested
2. **Parallel Processing**: Multi-threaded validation and database operations
3. **Connection Pooling**: Optimized MongoDB connection management
4. **Batch Processing**: Efficient chunk-based processing
5. **Memory Management**: Optimized memory usage with configurable chunk sizes
6. **Index Optimization**: Proper MongoDB indexing for fast queries

## 🧪 Testing

The system includes comprehensive testing capabilities:

- **Performance Tests**: Basic performance benchmarking
- **Comprehensive Tests**: Multi-parameter optimization testing
- **CSV I/O Tests**: Different reading strategy comparisons
- **Index Tests**: Database performance optimization
- **Memory Monitoring**: Real-time memory usage tracking

## 📊 Monitoring and Logging

- **Processing Logs**: Detailed processing statistics
- **Error Logs**: Comprehensive error reporting
- **Performance Metrics**: Speed, memory usage, and quality metrics
- **Validation Reports**: Data quality and validation statistics




