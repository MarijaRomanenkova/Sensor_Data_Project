import time
import logging
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from data_processing.processor import DataProcessor
from dateutil import parser

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def generate_test_data(num_records: int, output_file: str):
    """Generate a test dataset with the specified number of records."""
    # Use debug level for performance tests
    logger.debug(f"Generating test dataset with {num_records:,} records...")
    
    # Ensure the output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Generate timestamps
    end_time = datetime.now()
    start_time = end_time - timedelta(days=30)  # 30 days of data
    timestamps = pd.date_range(start=start_time, end=end_time, periods=num_records)
    
    # Generate random data
    data = {
        'timestamp': timestamps,
        'device_id': [f'Device_{i % 50 + 1}' for i in range(num_records)],  # 50 different devices
        'temperature': np.random.uniform(-10, 40, num_records).round(2),  # -10°C to 40°C
        'humidity': np.random.uniform(0, 100, num_records).round(2),  # 0-100%
        'pressure': np.random.uniform(800, 1200, num_records).round(2),  # 800-1200 hPa
        'light': np.random.randint(0, 1000, num_records),  # 0-1000 lux
        'sound': np.random.randint(0, 100, num_records),  # 0-100 dB
        'motion': np.random.randint(0, 2, num_records),  # 0 or 1
        'battery': np.random.uniform(0, 100, num_records).round(2),  # 0-100%
        'location': [f'Location_{i % 10 + 1}' for i in range(num_records)]  # 10 different locations
    }
    
    # Create DataFrame and save to CSV
    df = pd.DataFrame(data)
    df.to_csv(output_file, index=False)
    logger.debug(f"Test dataset saved to {output_file}")
    return df

def test_data_loading(num_records: int = 500000):
    """Test the system's performance with a large dataset."""
    processor = DataProcessor()
    test_file = "data/raw/test_large_dataset.csv"
    
    try:
        # Temporarily reduce logging level for processor
        processor_logger = logging.getLogger('data_processing.processor')
        original_level = processor_logger.level
        processor_logger.setLevel(logging.WARNING)
        
        # Connect to MongoDB
        processor.connect_to_mongodb()
        
        # Clean up existing data before test (NOT TIMED)
        logger.debug("Cleaning up existing data from the database...")
        processor.collection.delete_many({})
        logger.debug("Database cleanup completed")
        
        # Generate and process test data (NOT TIMED)
        logger.debug(f"Generating test dataset with {num_records:,} records...")
        generate_test_data(num_records, test_file)
        logger.debug(f"Test dataset saved to {test_file}")
        
        # TIMING STARTS HERE - only measure actual processing
        logger.debug(f"Starting to process {num_records:,} records...")
        start_time = time.time()
        result = processor.process_file_in_batches(test_file)
        end_time = time.time()
        # TIMING ENDS HERE
        
        # Calculate and log performance metrics
        duration = end_time - start_time
        records_per_second = result['processed_records'] / duration if duration > 0 else 0
        
        # Calculate memory usage
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_usage_mb = memory_info.rss / 1024 / 1024
        
        # Get data quality metrics
        quality_metrics = processor.get_data_quality_metrics()
        
        # Print performance results in a clear format
        logger.info("\n" + "="*50)
        logger.info("PERFORMANCE TEST RESULTS")
        logger.info("="*50)
        logger.info(f"Processing Time: {duration:.2f} seconds")
        logger.info(f"Processing Speed: {records_per_second:,.2f} records/second")
        logger.info(f"Memory Usage: {memory_usage_mb:.2f} MB")
        logger.info(f"Records Processed: {result['processed_records']:,}")
        logger.info(f"Failed Records: {result['failed_records']:,}")
        logger.info(f"Success Rate: {(result['processed_records'] / num_records * 100):.2f}%")
        
        # Move detailed quality metrics to debug level
        logger.debug("\n" + "="*50)
        logger.debug("DATA QUALITY METRICS")
        logger.debug("="*50)
        logger.debug(f"Data Quality Score: {quality_metrics['data_quality_score']:.2f}%")
        logger.debug(f"Missing Values: {quality_metrics['missing_values']:,}")
        logger.debug(f"Out of Range Values: {quality_metrics['out_of_range']:,}")
        logger.debug("="*50 + "\n")
        
        if processor.validation_errors:
            logger.warning(f"First 3 validation errors: {processor.validation_errors[:3]}")
        
        if processor.mongo_errors:
            logger.error(f"First 3 MongoDB errors: {processor.mongo_errors[:3]}")
        
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        raise
    finally:
        # Restore original logging level
        processor_logger.setLevel(original_level)
        processor.close()
        # Clean up the test file
        try:
            if os.path.exists(test_file):
                os.remove(test_file)
                logger.debug(f"Cleaned up test file: {test_file}")
        except Exception as e:
            logger.error(f"Error cleaning up test file: {str(e)}")

if __name__ == "__main__":
    # Test with 500,000 records
    test_data_loading(500000) 
