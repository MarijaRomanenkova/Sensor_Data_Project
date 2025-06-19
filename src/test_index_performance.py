import os
import time
import logging
import pandas as pd
from datetime import datetime
from data_processing.processor import DataProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_test_data(num_records: int, output_file: str):
    """Generate test data and save to CSV file."""
    logger.info(f"Generating {num_records:,} test records...")
    
    # Generate timestamps
    timestamps = pd.date_range(
        start='2024-01-01',
        periods=num_records,
        freq='S'
    )
    
    # Create DataFrame
    df = pd.DataFrame({
        'device_id': [f'device_{i % 1000}' for i in range(num_records)],
        'timestamp': timestamps,
        'temperature': [20 + (i % 10) for i in range(num_records)],
        'humidity': [50 + (i % 20) for i in range(num_records)],
        'pressure': [1013 + (i % 5) for i in range(num_records)],
        'location': [f'location_{i % 100}' for i in range(num_records)],
        'status': ['active' if i % 10 != 0 else 'inactive' for i in range(num_records)]
    })
    
    # Save to CSV
    df.to_csv(output_file, index=False)
    logger.info(f"Test data saved to {output_file}")
    return df

def test_with_indexes(processor: DataProcessor, file_path: str) -> dict:
    """Test performance with indexes."""
    logger.info("\n=== Testing with indexes ===")
    start_time = time.time()
    
    try:
        # Process the file using DataProcessor
        result = processor.process_file_in_batches(file_path)
        
        duration = time.time() - start_time
        return {
            "duration": duration,
            "records_per_second": result['processed_records'] / duration if duration > 0 else 0,
            "total_records": result['total_records'],
            "processed_records": result['processed_records'],
            "failed_records": result['failed_records']
        }
    except Exception as e:
        logger.error(f"Error in test with indexes: {str(e)}")
        raise

def test_without_indexes(processor: DataProcessor, file_path: str) -> dict:
    """Test performance without indexes."""
    logger.info("\n=== Testing without indexes ===")
    start_time = time.time()
    
    try:
        # Drop indexes before bulk loading
        processor.drop_indexes()
        
        # Process the file using DataProcessor
        result = processor.process_file_in_batches(file_path)
        
        # Recreate indexes after bulk loading
        processor.recreate_indexes()
        
        duration = time.time() - start_time
        return {
            "duration": duration,
            "records_per_second": result['processed_records'] / duration if duration > 0 else 0,
            "total_records": result['total_records'],
            "processed_records": result['processed_records'],
            "failed_records": result['failed_records']
        }
    except Exception as e:
        logger.error(f"Error in test without indexes: {str(e)}")
        # Ensure indexes are recreated even if test fails
        try:
            processor.recreate_indexes()
        except Exception as index_error:
            logger.error(f"Failed to recreate indexes after error: {str(index_error)}")
        raise

def main():
    """Main function to run the performance test."""
    # Test parameters
    num_records = 500_000
    test_file = "test_large_dataset.csv"
    
    try:
        # Generate test data
        generate_test_data(num_records, test_file)
        
        # Create processor instance
        processor = DataProcessor()
        
        # Connect to MongoDB
        processor.connect_to_mongodb()
        
        # Clean up existing data before test
        logger.info("Cleaning up existing data from the database...")
        processor.collection.delete_many({})
        logger.info("Database cleanup completed")
        
        # Run tests
        with_indexes = test_with_indexes(processor, test_file)
        
        # Clean up for second test
        logger.info("\nCleaning up for second test...")
        processor.collection.delete_many({})
        
        without_indexes = test_without_indexes(processor, test_file)
        
        # Calculate performance difference
        speed_diff = ((without_indexes["records_per_second"] - with_indexes["records_per_second"]) 
                     / with_indexes["records_per_second"] * 100)
        
        # Log results
        logger.info("\n=== Test Results ===")
        logger.info(f"With indexes:")
        logger.info(f"  Processing time: {with_indexes['duration']:.2f} seconds")
        logger.info(f"  Processing speed: {with_indexes['records_per_second']:.2f} records/second")
        logger.info(f"  Records processed: {with_indexes['processed_records']:,}")
        logger.info(f"  Failed records: {with_indexes['failed_records']:,}")
        logger.info(f"  Success rate: {(with_indexes['processed_records'] / with_indexes['total_records'] * 100):.2f}%")
        
        logger.info(f"\nWithout indexes:")
        logger.info(f"  Processing time: {without_indexes['duration']:.2f} seconds")
        logger.info(f"  Processing speed: {without_indexes['records_per_second']:.2f} records/second")
        logger.info(f"  Records processed: {without_indexes['processed_records']:,}")
        logger.info(f"  Failed records: {without_indexes['failed_records']:,}")
        logger.info(f"  Success rate: {(without_indexes['processed_records'] / without_indexes['total_records'] * 100):.2f}%")
        
        logger.info(f"\nPerformance difference: {speed_diff:+.2f}%")
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise
    finally:
        # Cleanup
        processor.close()
        if os.path.exists(test_file):
            os.remove(test_file)
            logger.info(f"Cleaned up test file: {test_file}")

if __name__ == "__main__":
    main()
