import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List
import json
from pathlib import Path
import concurrent.futures
from functools import partial

import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING
from pymongo.errors import PyMongoError

from config.settings import BATCH_SIZE

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime and Timestamp objects."""
    def default(self, obj):
        if isinstance(obj, (datetime, pd.Timestamp)):
            return obj.isoformat()
        return super().default(obj)


class DataProcessor:
    def __init__(self):
        load_dotenv()
        self.mongo_uri = os.getenv(
            "MONGODB_URI", "mongodb://admin:password123@localhost:27017/"
        )
        self.db_name = os.getenv("MONGODB_DB", "sensor_data")
        self.batch_size = BATCH_SIZE  # Use batch size from settings
        self.client = None
        self.db = None
        self.collection = None
        self.aggregated_collection = None
        
        # Create logs directory if it doesn't exist
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)
        
        # Initialize validation log file
        self.validation_log_path = self.logs_dir / f"validation_errors_{datetime.now().strftime('%Y%m%d')}.json"
        self.validation_errors = []
        
        # Column name mappings for normalization
        self.column_mappings = {
            # Timestamp variations
            'timestamp': ['timestamp', 'time', 'datetime', 'date_time', 'ts', 'Timestamp', 'TIME', 'DATETIME'],
            # Device ID variations
            'device_id': [
                'device_id', 'deviceid', 'device', 'id', 'deviceID', 'DeviceID', 'DEVICE_ID',
                'device_ID', 'Device_Id', 'DEVICE_ID', 'device-id', 'device.id', 'deviceId',
                'deviceID', 'DeviceId', 'DEVICEID', 'device_id_number', 'device_number'
            ],
            # Temperature variations
            'temperature': ['temperature', 'temp', 'Temperature', 'TEMP', 'Temperature_C', 'temp_c'],
            # Humidity variations
            'humidity': ['humidity', 'hum', 'Humidity', 'HUM', 'humidity_percent', 'humidity_pct'],
            # Pressure variations
            'pressure': ['pressure', 'Pressure', 'PRESSURE', 'pressure_value', 'pressure_value_hpa'],
            # Additional value fields
            'value1': ['value1', 'Value1', 'VALUE1', 'reading1', 'Reading1'],
            'value2': ['value2', 'Value2', 'VALUE2', 'reading2', 'Reading2'],
            'value3': ['value3', 'Value3', 'VALUE3', 'reading3', 'Reading3'],
            'value4': ['value4', 'Value4', 'VALUE4', 'reading4', 'Reading4'],
            # Location field
            'location': ['location', 'Location', 'LOCATION', 'room', 'Room', 'ROOM']
        }
        
        # Optimized connection pool settings
        self.pool_size = 50  # Increased pool size
        self.max_pool_size = 200  # Increased max pool size
        self.wait_queue_timeout_ms = 5000  # Increased timeout
        self.max_idle_time_ms = 120000  # Increased idle time
        self.connect_timeout_ms = 30000  # Increased connect timeout
        self.socket_timeout_ms = 30000  # Increased socket timeout
        
        # Parallel processing settings
        self.max_workers = os.cpu_count() or 4  # Use number of CPU cores

    def connect_to_mongodb(self):
        """Establish connection to MongoDB with optimized connection pooling."""
        try:
            self.client = MongoClient(
                self.mongo_uri,
                maxPoolSize=self.max_pool_size,
                minPoolSize=self.pool_size,
                waitQueueTimeoutMS=self.wait_queue_timeout_ms,
                maxIdleTimeMS=self.max_idle_time_ms,
                connectTimeoutMS=self.connect_timeout_ms,
                socketTimeoutMS=self.socket_timeout_ms,
                serverSelectionTimeoutMS=5000,
                retryWrites=True,
                retryReads=True
            )
            self.db = self.client[self.db_name]
            self.collection = self.db["sensor_readings"]
            self.aggregated_collection = self.db["aggregated_readings"]
            
            # Create indexes with background option
            self.collection.create_index(
                [("device_id", 1), ("timestamp", 1)],
                name="device_timestamp_idx",
                background=True
            )
            self.collection.create_index(
                [("timestamp", 1)],
                name="timestamp_idx",
                background=True
            )
            # Add index for location-based queries
            self.collection.create_index(
                [("location", 1)],
                name="location_idx",
                background=True
            )
            # Add compound index for device and location
            self.collection.create_index(
                [("device_id", 1), ("location", 1)],
                name="device_location_idx",
                background=True
            )
            
            # Create schema validation
            schema = {
                "validator": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["timestamp", "device_id", "temperature", "humidity", 
                                   "pressure", "location"],
                        "properties": {
                            "timestamp": {
                                "bsonType": "date"
                            },
                            "device_id": {
                                "bsonType": "string"
                            },
                            "temperature": {
                                "bsonType": "double",
                                "minimum": -50,
                                "maximum": 50
                            },
                            "humidity": {
                                "bsonType": "double",
                                "minimum": 0,
                                "maximum": 100
                            },
                            "pressure": {
                                "bsonType": "double",
                                "minimum": 800,
                                "maximum": 1200
                            },
                            "light": {
                                "bsonType": ["int", "null"],
                                "minimum": 0
                            },
                            "sound": {
                                "bsonType": ["int", "null"],
                                "minimum": 0
                            },
                            "motion": {
                                "bsonType": ["int", "null"],
                                "minimum": 0,
                                "maximum": 1
                            },
                            "battery": {
                                "bsonType": ["double", "null"],
                                "minimum": 0,
                                "maximum": 100
                            },
                            "location": {
                                "bsonType": "string"
                            },
                            "metadata": {
                                "bsonType": "object"
                            }
                        }
                    }
                }
            }
            
            # Apply schema validation
            self.db.command("collMod", self.collection.name, **schema)
            
            logger.info("Successfully connected to MongoDB with optimized connection pooling and schema validation")
        except PyMongoError as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise

    def cleanup_old_data(self):
        """Clean up data according to retention policy."""
        try:
            # Calculate cutoff dates
            one_year_ago = datetime.utcnow() - timedelta(days=365)
            five_years_ago = datetime.utcnow() - timedelta(days=365 * 5)

            # Delete raw data older than 1 year
            result = self.collection.delete_many({"timestamp": {"$lt": one_year_ago}})
            logger.info(f"Deleted {result.deleted_count} raw records older than 1 year")

            # Delete aggregated data older than 5 years
            result = self.aggregated_collection.delete_many({"timestamp": {"$lt": five_years_ago}})
            logger.info(f"Deleted {result.deleted_count} aggregated records older than 5 years")

        except PyMongoError as e:
            logger.error(f"Failed to cleanup old data: {str(e)}")
            raise

    def create_daily_aggregation(self):
        """Create daily aggregated data."""
        try:
            yesterday = datetime.utcnow() - timedelta(days=1)
            start_of_day = datetime(yesterday.year, yesterday.month, yesterday.day)
            end_of_day = start_of_day + timedelta(days=1)

            # Aggregate data for each device and location
            pipeline = [
                {
                    "$match": {
                        "timestamp": {
                            "$gte": start_of_day,
                            "$lt": end_of_day
                        }
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "device_id": "$device_id",
                            "location": "$location"
                        },
                        "avg_temperature": {"$avg": "$temperature"},
                        "avg_humidity": {"$avg": "$humidity"},
                        "avg_pressure": {"$avg": "$pressure"},
                        "avg_value1": {"$avg": "$value1"},
                        "avg_value2": {"$avg": "$value2"},
                        "avg_value3": {"$avg": "$value3"},
                        "avg_value4": {"$avg": "$value4"},
                        "max_temperature": {"$max": "$temperature"},
                        "min_temperature": {"$min": "$temperature"},
                        "count": {"$sum": 1}
                    }
                }
            ]

            aggregated_data = list(self.collection.aggregate(pipeline))
            
            # Add metadata and insert into aggregated collection
            for record in aggregated_data:
                record["timestamp"] = start_of_day
                record["device_id"] = record["_id"]["device_id"]
                record["location"] = record["_id"]["location"]
                del record["_id"]
                record["metadata"] = {
                    "aggregated_at": datetime.utcnow(),
                    "period": "daily"
                }
                self.aggregated_collection.insert_one(record)

            logger.info(f"Created daily aggregation for {len(aggregated_data)} device-location combinations")
            return aggregated_data

        except PyMongoError as e:
            logger.error(f"Failed to create daily aggregation: {str(e)}")
            raise

    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate sensor data, tolerate missing/inconsistent fields, log and skip invalid records."""
        try:
            # First try with original field names
            if self._validate_fields(data):
                return True

            # If validation fails, try with normalized field names
            normalized_data = self._normalize_record_fields(data)
            if normalized_data and self._validate_fields(normalized_data):
                # Update the original data with normalized values
                data.update(normalized_data)
                return True

            return False
        except Exception as e:
            logger.warning(f"Validation error: {str(e)}")
            return False

    def _log_validation_error(self, record: Dict[str, Any], error_reason: str):
        """Log validation error with record details and reason."""
        # Convert any Timestamp objects to ISO format strings
        processed_record = {}
        for key, value in record.items():
            if isinstance(value, (datetime, pd.Timestamp)):
                processed_record[key] = value.isoformat()
            else:
                processed_record[key] = value

        # Get actual values for validation fields
        validation_values = {
            field: processed_record.get(field, "MISSING")
            for field in ["timestamp", "device_id", "temperature", "humidity", "pressure",
                         "value1", "value2", "value3", "value4", "location"]
        }

        error_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_reason": error_reason,
            "record": processed_record,
            "original_fields": list(record.keys()),
            "validation_values": validation_values,
            "data_types": {
                field: str(type(processed_record.get(field, None)).__name__)
                for field in ["timestamp", "device_id", "temperature", "humidity", "pressure",
                            "value1", "value2", "value3", "value4", "location"]
            }
        }
        self.validation_errors.append(error_entry)
        
        # Log detailed error information
        logger.warning(
            f"Validation Error: {error_reason}\n"
            f"Record values: {validation_values}\n"
            f"Data types: {error_entry['data_types']}\n"
            f"Original fields: {list(record.keys())}"
        )
        
        # Write to file periodically (every 100 errors)
        if len(self.validation_errors) >= 100:
            self._flush_validation_log()

    def _flush_validation_log(self):
        """Flush validation errors to log file."""
        if not self.validation_errors:
            return
            
        try:
            # Create a temporary file for atomic write
            temp_path = self.validation_log_path.with_suffix('.tmp')
            
            # Read existing errors if file exists
            existing_errors = []
            if self.validation_log_path.exists():
                try:
                    with open(self.validation_log_path, 'r') as f:
                        existing_errors = json.load(f)
                except json.JSONDecodeError:
                    logger.warning("Existing validation log file is corrupted, starting fresh")
            
            # Write to temporary file using custom encoder
            with open(temp_path, 'w') as f:
                json.dump(existing_errors + self.validation_errors, f, indent=2, cls=DateTimeEncoder)
            
            # Atomic rename
            temp_path.replace(self.validation_log_path)
            
            # Clear the buffer
            self.validation_errors = []
            
        except Exception as e:
            logger.error(f"Failed to write validation log: {str(e)}")
            # Keep errors in memory if write fails
            logger.warning("Keeping validation errors in memory due to write failure")

    def _validate_fields(self, data: Dict[str, Any]) -> bool:
        """Internal method to validate fields with given field names."""
        try:
            # Log validation attempt for debugging
            logger.debug(f"Validating record: {data}")
            
            # Check for required fields
            required_fields = ["timestamp", "device_id", "temperature", "humidity", 
                             "pressure", "location"]
            for field in required_fields:
                if field not in data or data[field] is None:
                    self._log_validation_error(data, f"Missing or null field: {field}")
                    logger.debug(f"Missing field: {field}")
                    return False

            # Log field values and types for debugging
            logger.debug("Field values and types:")
            for field in data:
                logger.debug(f"{field}: {data[field]} ({type(data[field]).__name__})")

            # Type validation (tolerant)
            if not isinstance(data["timestamp"], (str, datetime)):
                self._log_validation_error(data, f"Invalid timestamp type: {type(data.get('timestamp'))}")
                logger.debug(f"Invalid timestamp type: {type(data.get('timestamp'))}")
                return False
            if not isinstance(data["device_id"], str):
                self._log_validation_error(data, f"Invalid device_id type: {type(data.get('device_id'))}")
                logger.debug(f"Invalid device_id type: {type(data.get('device_id'))}")
                return False
            if not isinstance(data["temperature"], (int, float)):
                self._log_validation_error(data, f"Invalid temperature type: {type(data.get('temperature'))}")
                logger.debug(f"Invalid temperature type: {type(data.get('temperature'))}")
                return False
            if not isinstance(data["humidity"], (int, float)):
                self._log_validation_error(data, f"Invalid humidity type: {type(data.get('humidity'))}")
                logger.debug(f"Invalid humidity type: {type(data.get('humidity'))}")
                return False
            if not isinstance(data["pressure"], (int, float)):
                self._log_validation_error(data, f"Invalid pressure type: {type(data.get('pressure'))}")
                logger.debug(f"Invalid pressure type: {type(data.get('pressure'))}")
                return False
            if not isinstance(data["location"], str):
                self._log_validation_error(data, f"Invalid location type: {type(data.get('location'))}")
                logger.debug(f"Invalid location type: {type(data.get('location'))}")
                return False

            # Optional fields type validation
            for field, field_type in [
                ("light", int),
                ("sound", int),
                ("motion", int),
                ("battery", (int, float))
            ]:
                if field in data and data[field] is not None:
                    if not isinstance(data[field], field_type):
                        self._log_validation_error(data, f"Invalid {field} type: {type(data.get(field))}")
                        logger.debug(f"Invalid {field} type: {type(data.get(field))}")
                        return False

            # Range validation (tolerant)
            if not -50 <= float(data["temperature"]) <= 50:
                self._log_validation_error(data, f"Temperature out of range: {data['temperature']}")
                logger.debug(f"Temperature out of range: {data['temperature']}")
                return False
            if not 0 <= float(data["humidity"]) <= 100:
                self._log_validation_error(data, f"Humidity out of range: {data['humidity']}")
                logger.debug(f"Humidity out of range: {data['humidity']}")
                return False
            if not 800 <= float(data["pressure"]) <= 1200:  # Typical atmospheric pressure range in hPa
                self._log_validation_error(data, f"Pressure out of range: {data['pressure']}")
                logger.debug(f"Pressure out of range: {data['pressure']}")
                return False

            # Optional fields range validation
            if "light" in data and data["light"] is not None and not 0 <= int(data["light"]):
                self._log_validation_error(data, f"Light out of range: {data['light']}")
                logger.debug(f"Light out of range: {data['light']}")
                return False
            if "sound" in data and data["sound"] is not None and not 0 <= int(data["sound"]):
                self._log_validation_error(data, f"Sound out of range: {data['sound']}")
                logger.debug(f"Sound out of range: {data['sound']}")
                return False
            if "motion" in data and data["motion"] is not None and not 0 <= int(data["motion"]) <= 1:
                self._log_validation_error(data, f"Motion out of range: {data['motion']}")
                logger.debug(f"Motion out of range: {data['motion']}")
                return False
            if "battery" in data and data["battery"] is not None and not 0 <= float(data["battery"]) <= 100:
                self._log_validation_error(data, f"Battery out of range: {data['battery']}")
                logger.debug(f"Battery out of range: {data['battery']}")
                return False

            return True
        except Exception as e:
            self._log_validation_error(data, f"Validation error: {str(e)}")
            logger.debug(f"Validation exception: {str(e)}")
            return False

    def _normalize_record_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize field names in a single record."""
        normalized_data = {}
        reverse_mapping = {}
        
        # Create reverse mapping for easier lookup
        for standard_name, variations in self.column_mappings.items():
            for var in variations:
                reverse_mapping[var.lower()] = standard_name

        # Try to map each field to its standard name
        for key, value in data.items():
            key_lower = key.lower()
            if key_lower in reverse_mapping:
                normalized_data[reverse_mapping[key_lower]] = value

        return normalized_data

    def process_batch(self, batch: List[Dict[str, Any]]) -> int:
        """Process a batch of records and insert valid ones into MongoDB."""
        valid_records = []
        batch_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        batch_stats = {
            "total": len(batch),
            "normalized": 0,
            "valid": 0,
            "invalid": 0,
            "error_types": {}
        }

        logger.info(f"\n=== Processing Batch {batch_id} ===")
        logger.info(f"Batch size: {len(batch)} records")

        # Pre-normalize column names for the entire batch
        normalized_batch = []
        for record in batch:
            normalized_record = self._normalize_record_fields(record)
            if normalized_record:
                normalized_batch.append(normalized_record)
                batch_stats["normalized"] += 1

        logger.info(f"Normalized records: {batch_stats['normalized']}")

        # Validate records in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            validation_results = list(executor.map(self._validate_fields, normalized_batch))

        # Collect valid records and update stats
        for record, is_valid in zip(normalized_batch, validation_results):
            if is_valid:
                record["metadata"] = {
                    "batch_id": batch_id,
                    "processed_at": datetime.utcnow(),
                }
                valid_records.append(record)
                batch_stats["valid"] += 1
            else:
                batch_stats["invalid"] += 1

        # Log batch statistics
        logger.info(
            f"\nBatch {batch_id} Statistics:\n"
            f"Total records: {batch_stats['total']}\n"
            f"Normalized records: {batch_stats['normalized']}\n"
            f"Valid records: {batch_stats['valid']}\n"
            f"Invalid records: {batch_stats['invalid']}\n"
            f"Success rate: {(batch_stats['valid'] / batch_stats['total'] * 100):.2f}%"
        )

        if valid_records:
            try:
                # Use ordered=False for better performance
                result = self.collection.insert_many(valid_records, ordered=False)
                logger.info(f"Successfully inserted {len(result.inserted_ids)} records")
                return len(result.inserted_ids)
            except PyMongoError as e:
                logger.error(f"Failed to insert records: {str(e)}")
                return 0
        return 0

    def normalize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to handle case sensitivity and common variations."""
        column_mapping = {}
        
        # Create reverse mapping for easier lookup
        reverse_mapping = {}
        for standard_name, variations in self.column_mappings.items():
            for var in variations:
                reverse_mapping[var.lower()] = standard_name
        
        # Map existing columns to standard names
        for col in df.columns:
            col_lower = col.lower()
            if col_lower in reverse_mapping:
                column_mapping[col] = reverse_mapping[col_lower]
            else:
                logger.warning(f"Unknown column name: {col}")
        
        # Rename columns
        df = df.rename(columns=column_mapping)
        
        # Check for missing required columns
        required_columns = set(self.column_mappings.keys())
        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        return df

    def process_file_in_batches(self, file_path: str) -> Dict[str, int]:
        """Process a CSV file in chunks with parallel processing."""
        try:
            logger.info(f"Starting to process file: {file_path}")
            total_records = 0
            processed_records = 0
            file_stats = {
                "total_batches": 0,
                "total_records": 0,
                "processed_records": 0,
                "failed_records": 0,
                "start_time": datetime.utcnow(),
                "batch_stats": []
            }
            
            # Read CSV in chunks with optimized settings
            logger.info("Reading CSV file in chunks...")
            for chunk in pd.read_csv(
                file_path,
                chunksize=self.batch_size,
                parse_dates=['timestamp'],
                infer_datetime_format=True,
                low_memory=False
            ):
                # Log sample data for debugging
                if total_records == 0:
                    logger.info("\n=== First Chunk Details ===")
                    logger.info(f"Columns: {chunk.columns.tolist()}")
                    logger.info(f"First row: {chunk.iloc[0].to_dict()}")
                    logger.info(f"Data types:\n{chunk.dtypes}")
                    # Add raw data logging
                    with open(file_path, 'r') as f:
                        first_line = f.readline().strip()
                        logger.info(f"Raw first line from file: {first_line}")
                
                # Convert to list of dictionaries
                records = chunk.to_dict("records")
                total_records += len(records)
                file_stats["total_records"] = total_records
                file_stats["total_batches"] += 1
                
                # Log first record details for debugging
                if records:
                    first_record = records[0]
                    logger.info(f"\nFirst record after conversion: {first_record}")
                    logger.info(f"First record types: {[(k, type(v).__name__) for k, v in first_record.items()]}")
                
                # Process the batch
                logger.info(f"\nProcessing batch {file_stats['total_batches']}...")
                batch_processed = self.process_batch(records)
                processed_records += batch_processed
                file_stats["processed_records"] = processed_records
                file_stats["failed_records"] = total_records - processed_records
                
                # Calculate and log progress
                progress = (processed_records / total_records * 100) if total_records > 0 else 0
                logger.info(f"Progress: {progress:.2f}% ({processed_records}/{total_records} records)")
            
            # Log final file statistics
            duration = (datetime.utcnow() - file_stats["start_time"]).total_seconds()
            logger.info(
                f"\n=== File Processing Complete ===\n"
                f"Total records: {file_stats['total_records']}\n"
                f"Processed records: {file_stats['processed_records']}\n"
                f"Failed records: {file_stats['failed_records']}\n"
                f"Total batches: {file_stats['total_batches']}\n"
                f"Processing time: {duration:.2f} seconds\n"
                f"Average speed: {file_stats['total_records'] / duration:.2f} records/second"
            )
            
            return {
                "total_records": total_records,
                "processed_records": processed_records,
                "failed_records": total_records - processed_records
            }
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            raise

    def close(self):
        """Close MongoDB connection and flush any remaining validation logs."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
        
        # Flush any remaining validation errors
        if self.validation_errors:
            self._flush_validation_log()
            logger.info(f"Validation errors logged to {self.validation_log_path}")

    def get_data_quality_metrics(self) -> Dict[str, Any]:
        """Calculate data quality metrics."""
        try:
            # Get total records
            total_records = self.collection.count_documents({})
            
            # Get records with missing values
            missing_values = self.collection.count_documents({
                "$or": [
                    {"temperature": None},
                    {"humidity": None},
                    {"pressure": None}
                ]
            })
            
            # Get records with out-of-range values
            out_of_range = self.collection.count_documents({
                "$or": [
                    {"temperature": {"$lt": -50, "$gt": 50}},
                    {"humidity": {"$lt": 0, "$gt": 100}},
                    {"pressure": {"$lt": 800, "$gt": 1200}}
                ]
            })
            
            return {
                "total_records": total_records,
                "missing_values": missing_values,
                "out_of_range": out_of_range,
                "data_quality_score": ((total_records - missing_values - out_of_range) / total_records) * 100 if total_records > 0 else 0
            }
        except PyMongoError as e:
            logger.error(f"Failed to calculate data quality metrics: {str(e)}")
            raise

    def get_validation_summary(self) -> Dict[str, Any]:
        """Get a summary of validation errors."""
        try:
            if not self.validation_log_path.exists():
                return {"total_errors": 0, "error_types": {}}
            
            with open(self.validation_log_path, 'r') as f:
                errors = json.load(f)
            
            error_types = {}
            for error in errors:
                error_reason = error["error_reason"]
                error_types[error_reason] = error_types.get(error_reason, 0) + 1
            
            return {
                "total_errors": len(errors),
                "error_types": error_types,
                "log_file": str(self.validation_log_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to get validation summary: {str(e)}")
            return {"error": str(e)}

    def query_data(self, query: Dict[str, Any] = None, limit: int = 10, sort_by: str = "timestamp", sort_order: int = -1) -> List[Dict[str, Any]]:
        """Query the database with optional filtering, sorting, and limit.
        
        Args:
            query: MongoDB query dictionary (e.g., {"device_id": "Device_21"})
            limit: Maximum number of records to return
            sort_by: Field to sort by
            sort_order: 1 for ascending, -1 for descending
        
        Returns:
            List of matching records
        """
        try:
            if query is None:
                query = {}
            
            # Convert string timestamps to datetime if present in query
            if "timestamp" in query and isinstance(query["timestamp"], str):
                query["timestamp"] = datetime.fromisoformat(query["timestamp"])
            
            # Execute query with sorting and limit
            cursor = self.collection.find(query).sort(sort_by, sort_order).limit(limit)
            
            # Convert cursor to list and format timestamps
            results = []
            for doc in cursor:
                # Convert ObjectId to string for JSON serialization
                doc["_id"] = str(doc["_id"])
                # Convert datetime to ISO format
                if "timestamp" in doc:
                    doc["timestamp"] = doc["timestamp"].isoformat()
                if "metadata" in doc and "processed_at" in doc["metadata"]:
                    doc["metadata"]["processed_at"] = doc["metadata"]["processed_at"].isoformat()
                results.append(doc)
            
            return results
            
        except Exception as e:
            logger.error(f"Error querying database: {str(e)}")
            raise

    def get_device_stats(self, device_id: str = None) -> Dict[str, Any]:
        """Get statistics for a specific device or all devices.
        
        Args:
            device_id: Optional device ID to filter by
        
        Returns:
            Dictionary containing statistics
        """
        try:
            pipeline = []
            
            # Only add match stage if device_id is provided
            if device_id:
                pipeline.append({"$match": {"device_id": device_id}})
            
            # Add group stage
            pipeline.append({
                "$group": {
                    "_id": "$device_id",
                    "avg_temperature": {"$avg": "$temperature"},
                    "avg_humidity": {"$avg": "$humidity"},
                    "avg_pressure": {"$avg": "$pressure"},
                    "avg_light": {"$avg": "$light"},
                    "avg_sound": {"$avg": "$sound"},
                    "avg_battery": {"$avg": "$battery"},
                    "total_readings": {"$sum": 1},
                    "locations": {"$addToSet": "$location"},
                    "first_reading": {"$min": "$timestamp"},
                    "last_reading": {"$max": "$timestamp"}
                }
            })
            
            results = list(self.collection.aggregate(pipeline))
            
            # Format the results
            for result in results:
                result["device_id"] = result.pop("_id")
                result["first_reading"] = result["first_reading"].isoformat()
                result["last_reading"] = result["last_reading"].isoformat()
            
            return results[0] if device_id and results else results
            
        except Exception as e:
            logger.error(f"Error getting device stats: {str(e)}")
            raise

    def get_location_stats(self, location: str = None) -> Dict[str, Any]:
        """Get statistics for a specific location or all locations.
        
        Args:
            location: Optional location to filter by
        
        Returns:
            Dictionary containing statistics
        """
        try:
            pipeline = []
            
            # Only add match stage if location is provided
            if location:
                pipeline.append({"$match": {"location": location}})
            
            # Add group stage
            pipeline.append({
                "$group": {
                    "_id": "$location",
                    "avg_temperature": {"$avg": "$temperature"},
                    "avg_humidity": {"$avg": "$humidity"},
                    "avg_pressure": {"$avg": "$pressure"},
                    "avg_light": {"$avg": "$light"},
                    "avg_sound": {"$avg": "$sound"},
                    "device_count": {"$addToSet": "$device_id"},
                    "total_readings": {"$sum": 1},
                    "first_reading": {"$min": "$timestamp"},
                    "last_reading": {"$max": "$timestamp"}
                }
            })
            
            results = list(self.collection.aggregate(pipeline))
            
            # Format the results
            for result in results:
                result["location"] = result.pop("_id")
                result["device_count"] = len(result["device_count"])
                result["first_reading"] = result["first_reading"].isoformat()
                result["last_reading"] = result["last_reading"].isoformat()
            
            return results[0] if location and results else results
            
        except Exception as e:
            logger.error(f"Error getting location stats: {str(e)}")
            raise
