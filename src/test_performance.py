import time
import logging
from data_processing.processor import DataProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def test_data_loading():
    processor = DataProcessor()
    start_time = time.time()
    
    try:
        # Connect to MongoDB
        processor.connect_to_mongodb()
        
        # Process the test file
        file_path = "data/raw/real_time_data.csv"
        logger.info(f"Starting to process file: {file_path}")
        
        result = processor.process_file_in_batches(file_path)
        
        # Calculate and log performance metrics
        end_time = time.time()
        duration = end_time - start_time
        records_per_second = result['processed_records'] / duration if duration > 0 else 0
        
        logger.info("Performance Results:")
        logger.info(f"Total time: {duration:.2f} seconds")
        logger.info(f"Total records processed: {result['processed_records']}")
        logger.info(f"Processing speed: {records_per_second:.2f} records/second")
        logger.info(f"Failed records: {result['failed_records']}")
        
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        raise
    finally:
        processor.close()

if __name__ == "__main__":
    test_data_loading() 
