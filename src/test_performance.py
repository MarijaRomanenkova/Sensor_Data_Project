import time
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_processing.processor import DataProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def generate_test_data(num_records: int, output_file: str):
    """Generate a test dataset with the specified number of records."""
    logger.info(f"Generating test dataset with {num_records:,} records...")
    
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
    logger.info(f"Test dataset saved to {output_file}")
    return df

def test_data_loading(num_records: int = 500000):
    """Test the system's performance with a large dataset."""
    processor = DataProcessor()
    start_time = time.time()
    
    try:
        # Connect to MongoDB
        processor.connect_to_mongodb()
        
        # Generate and process test data
        test_file = "data/raw/test_large_dataset.csv"
        generate_test_data(num_records, test_file)
        
        logger.info(f"Starting to process {num_records:,} records...")
        result = processor.process_file_in_batches(test_file)
        
        # Calculate and log performance metrics
        end_time = time.time()
        duration = end_time - start_time
        records_per_second = result['processed_records'] / duration if duration > 0 else 0
        
        logger.info("\n=== Performance Test Results ===")
        logger.info(f"Total time: {duration:.2f} seconds")
        logger.info(f"Total records processed: {result['processed_records']:,}")
        logger.info(f"Processing speed: {records_per_second:.2f} records/second")
        logger.info(f"Failed records: {result['failed_records']:,}")
        logger.info(f"Success rate: {(result['processed_records'] / num_records * 100):.2f}%")
        
        # Calculate memory usage
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        logger.info(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")
        
        # Get data quality metrics
        quality_metrics = processor.get_data_quality_metrics()
        logger.info("\n=== Data Quality Metrics ===")
        logger.info(f"Data quality score: {quality_metrics['data_quality_score']:.2f}%")
        logger.info(f"Missing values: {quality_metrics['missing_values']:,}")
        logger.info(f"Out of range values: {quality_metrics['out_of_range']:,}")
        
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        raise
    finally:
        processor.close()

if __name__ == "__main__":
    # Test with 500,000 records
    test_data_loading(500000) 
