import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
import json
from pathlib import Path
import concurrent.futures
from functools import partial
import time
import math
import gc
import tracemalloc
import psutil
from dateutil import parser

import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING
from pymongo.errors import PyMongoError

from config.settings import (
    BATCH_SIZE, CHUNK_SIZE, VALIDATION_CHUNK_SIZE, MAX_WORKERS,
    MONGODB_POOL_SIZE, MONGODB_MAX_POOL_SIZE, MONGODB_WAIT_QUEUE_TIMEOUT_MS,
    MONGODB_MAX_IDLE_TIME_MS, MONGODB_CONNECT_TIMEOUT_MS, MONGODB_SOCKET_TIMEOUT_MS,
    MONGODB_INSERT_BATCH_SIZE, MONGODB_COLLECTION,
    TEMPERATURE_RANGE, HUMIDITY_RANGE, PRESSURE_RANGE,
    LIGHT_RANGE, SOUND_RANGE, MOTION_RANGE, BATTERY_RANGE,
    MONGODB_URI, MONGODB_DB
)

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
        """Initialize the data processor with MongoDB connection and thread pool."""
        load_dotenv()
        self.mongo_uri = MONGODB_URI
        self.db_name = MONGODB_DB
        self.batch_size = BATCH_SIZE  # Use batch size from settings
        self.client = None
        self.db = None
        self.collection = None
        
        # Set number of worker threads from settings
        self.max_workers = MAX_WORKERS
        
        # Create logs directory if it doesn't exist
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)
        
        # Initialize validation log file
        self.validation_log_path = self.logs_dir / f"validation_errors_{datetime.now().strftime('%Y%m%d')}.json"
        
        # Initialize error collectors
        self.validation_errors = []
        self.mongo_errors = []
        self.processing_errors = []
        
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
        
        # Create reverse mapping for field normalization (do this once)
        self.reverse_mapping = {}
        for standard_name, variations in self.column_mappings.items():
            for var in variations:
                self.reverse_mapping[var.lower()] = standard_name
        
        # Optimized connection pool settings from settings
        self.pool_size = MONGODB_POOL_SIZE
        self.max_pool_size = MONGODB_MAX_POOL_SIZE
        self.wait_queue_timeout_ms = MONGODB_WAIT_QUEUE_TIMEOUT_MS
        self.max_idle_time_ms = MONGODB_MAX_IDLE_TIME_MS
        self.connect_timeout_ms = MONGODB_CONNECT_TIMEOUT_MS
        self.socket_timeout_ms = MONGODB_SOCKET_TIMEOUT_MS
        
        # Initialize field validators for validation logic
        self.field_validators = self._initialize_field_validators()

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
            self.collection = self.db[MONGODB_COLLECTION]
            
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
                                "minimum": TEMPERATURE_RANGE[0],
                                "maximum": TEMPERATURE_RANGE[1]
                            },
                            "humidity": {
                                "bsonType": "double",
                                "minimum": HUMIDITY_RANGE[0],
                                "maximum": HUMIDITY_RANGE[1]
                            },
                            "pressure": {
                                "bsonType": "double",
                                "minimum": PRESSURE_RANGE[0],
                                "maximum": PRESSURE_RANGE[1]
                            },
                            "light": {
                                "bsonType": ["int", "null"],
                                "minimum": LIGHT_RANGE[0]
                            },
                            "sound": {
                                "bsonType": ["int", "null"],
                                "minimum": SOUND_RANGE[0]
                            },
                            "motion": {
                                "bsonType": ["int", "null"],
                                "minimum": MOTION_RANGE[0],
                                "maximum": MOTION_RANGE[1]
                            },
                            "battery": {
                                "bsonType": ["double", "null"],
                                "minimum": BATTERY_RANGE[0],
                                "maximum": BATTERY_RANGE[1]
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

    def validate_data(self, record: Dict[str, Any]) -> bool:
        """Validate a single record."""
        try:
            # Normalize record fields
            normalized_record = self._normalize_record_fields(record)
            if not normalized_record:
                self.validation_errors.append({
                    'type': 'normalization_failed',
                    'record': record
                })
                return False

            # Validate fields
            if not self._validate_fields(normalized_record):
                self.validation_errors.append({
                    'type': 'validation_failed',
                    'record': normalized_record
                })
                return False
            return True
        except Exception as e:
            self.validation_errors.append({
                'type': 'validation_error',
                'error': str(e)
            })
            return False

    def _validate_fields(self, record: Dict[str, Any]) -> bool:
        """Validate all fields in a record."""
        try:
            for field, value in record.items():
                if not self._validate_field(field, value):
                    self.validation_errors.append({
                        'type': 'field_validation_failed',
                        'field': field,
                        'value': value
                    })
                    return False
            return True
        except Exception as e:
            self.validation_errors.append({
                'type': 'field_validation_error',
                'error': str(e)
            })
            return False

    def _validate_field(self, field: str, value: Any) -> bool:
        """Validate a single field value."""
        try:
            if field not in self.field_validators:
                return True

            validator = self.field_validators[field]
            if not validator(value):
                self.validation_errors.append({
                    'type': 'validator_failed',
                    'field': field,
                    'value': value
                })
                return False
            return True
        except Exception as e:
            self.validation_errors.append({
                'type': 'validator_error',
                'field': field,
                'error': str(e)
            })
            return False

    def _normalize_record_fields(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalize field names in a record."""
        try:
            normalized = {}
            for key, value in record.items():
                normalized_key = self._normalize_field_name(key)
                if normalized_key:
                    normalized[normalized_key] = value
            return normalized
        except Exception:
            return None

    def _normalize_field_name(self, field_name: str) -> Optional[str]:
        """Normalize a field name using the reverse mapping."""
        try:
            return self.reverse_mapping.get(field_name.lower())
        except Exception:
            return None

    def _initialize_field_validators(self) -> Dict[str, Callable]:
        """Initialize field validators."""
        return {
            'timestamp': lambda x: isinstance(x, (str, datetime)),
            'device_id': lambda x: isinstance(x, str),
            'temperature': lambda x: isinstance(x, (int, float)) and TEMPERATURE_RANGE[0] <= float(x) <= TEMPERATURE_RANGE[1],
            'humidity': lambda x: isinstance(x, (int, float)) and HUMIDITY_RANGE[0] <= float(x) <= HUMIDITY_RANGE[1],
            'pressure': lambda x: isinstance(x, (int, float)) and PRESSURE_RANGE[0] <= float(x) <= PRESSURE_RANGE[1],
            'location': lambda x: isinstance(x, str)
        }

    def process_file_in_batches(self, file_path: str) -> Dict[str, int]:
        """Process a CSV file in chunks with optimized MongoDB operations."""
        try:
            file_stats = {
                'total_records': 0,
                'processed_records': 0,
                'failed_records': 0,
                'total_chunks': 0
            }
            
            # Process file in chunks
            for chunk in pd.read_csv(file_path, chunksize=CHUNK_SIZE):
                file_stats['total_records'] += len(chunk)
                file_stats['total_chunks'] += 1
                
                # Convert chunk to records
                records = chunk.to_dict('records')
                
                # Process chunk directly (no batch splitting)
                processed = self.process_chunk(records)
                file_stats['processed_records'] += processed
            
            # Calculate final statistics
            file_stats['failed_records'] = file_stats['total_records'] - file_stats['processed_records']
            success_rate = (file_stats['processed_records'] / file_stats['total_records'] * 100) if file_stats['total_records'] > 0 else 0
            # Log final summary including error statistics
            logger.info("\n=== Processing Summary ===")
            logger.info(f"Total Records: {file_stats['total_records']:,}")
            logger.info(f"Success Rate: {success_rate:.2f}%")
            logger.info(f"Failed Records: {file_stats['failed_records']:,}")
            # Log error summaries
            if self.validation_errors:
                logger.warning(f"\nValidation Errors: {len(self.validation_errors)}")
                # Log most common validation errors
                error_counts = {}
                for error in self.validation_errors:
                    error_type = error.get('type', 'unknown')
                    error_counts[error_type] = error_counts.get(error_type, 0) + 1
                for error_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                    logger.warning(f"- {error_type}: {count} occurrences")
            if self.mongo_errors:
                logger.error(f"\nMongoDB Errors: {len(self.mongo_errors)}")
                # Log most common MongoDB errors
                error_counts = {}
                for error in self.mongo_errors:
                    error_type = error.get('type', 'unknown')
                    error_counts[error_type] = error_counts.get(error_type, 0) + 1
                for error_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                    logger.error(f"- {error_type}: {count} occurrences")
            if self.processing_errors:
                logger.error(f"\nProcessing Errors: {len(self.processing_errors)}")
                # Log most common processing errors
                error_counts = {}
                for error in self.processing_errors:
                    error_type = error.get('type', 'unknown')
                    error_counts[error_type] = error_counts.get(error_type, 0) + 1
                for error_type, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                    logger.error(f"- {error_type}: {count} occurrences")
            return file_stats
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            raise

    def process_chunk(self, records: List[Dict[str, Any]]) -> int:
        """Process a chunk of records with optimized MongoDB operations, validating in chunks from settings."""
        total_inserted = 0
        for i in range(0, len(records), VALIDATION_CHUNK_SIZE):
            validation_chunk = records[i:i + VALIDATION_CHUNK_SIZE]
            # Validate records in parallel for this chunk
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                validation_results = list(executor.map(self.validate_data, validation_chunk))
            # Filter valid records
            valid_records = [record for record, is_valid in zip(validation_chunk, validation_results) if is_valid]
            # Convert 'timestamp' field to datetime if it's a string
            for record in valid_records:
                if 'timestamp' in record and isinstance(record['timestamp'], str):
                    try:
                        record['timestamp'] = parser.parse(record['timestamp'])
                    except Exception:
                        self.validation_errors.append({
                            'type': 'timestamp_conversion_failed',
                            'record': record
                        })
                        record['timestamp'] = None
            valid_records = [r for r in valid_records if r.get('timestamp') is not None]
            if not valid_records:
                continue
            # Insert valid records in parallel (using fixed batch size from settings)
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                sub_batches = [valid_records[j:j + MONGODB_INSERT_BATCH_SIZE] for j in range(0, len(valid_records), MONGODB_INSERT_BATCH_SIZE)]
                def insert_sub_batch(sub_batch):
                    try:
                        result = self.collection.insert_many(sub_batch, ordered=False)
                        return len(result.inserted_ids)
                    except Exception as e:
                        self.mongo_errors.append({
                            'type': type(e).__name__,
                            'message': str(e)
                        })
                        return 0
                results = list(executor.map(insert_sub_batch, sub_batches))
                total_inserted += sum(results)
        return total_inserted

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

    def close(self):
        """Close MongoDB connection and flush any remaining validation logs."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
        
        # Log summary of collected errors if any exist
        if self.validation_errors or self.mongo_errors or self.processing_errors:
            logger.info(f"Error summary - Validation: {len(self.validation_errors)}, MongoDB: {len(self.mongo_errors)}, Processing: {len(self.processing_errors)}")

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
                    {"temperature": {"$lt": TEMPERATURE_RANGE[0], "$gt": TEMPERATURE_RANGE[1]}},
                    {"humidity": {"$lt": HUMIDITY_RANGE[0], "$gt": HUMIDITY_RANGE[1]}},
                    {"pressure": {"$lt": PRESSURE_RANGE[0], "$gt": PRESSURE_RANGE[1]}}
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
