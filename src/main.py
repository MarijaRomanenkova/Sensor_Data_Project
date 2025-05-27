import logging
import os

from data_processing.processor import DataProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def is_data_loaded(processor: DataProcessor) -> bool:
    """Check if data is already loaded in the database."""
    try:
        # Check if there are any records in the collection
        count = processor.collection.count_documents({})
        if count > 0:
            logger.info(f"Database already contains {count:,} records")
            return True
        return False
    except Exception as e:
        logger.error(f"Error checking if data is loaded: {str(e)}")
        return False

def main():
    processor = DataProcessor()
    try:
        # Connect to MongoDB
        processor.connect_to_mongodb()
        
        # Check if data is already loaded
        if is_data_loaded(processor):
            logger.info("Data is already loaded. Skipping data loading process.")
            return
        
        # Process data from CSV files
        data_dir = "data/raw"
        csv_files = [
            os.path.join(data_dir, "real_time_data.csv")
        ]
        
        for csv_file in csv_files:
            if not os.path.exists(csv_file):
                logger.warning(f"File not found: {csv_file}")
                continue
                
            logger.info(f"Processing file: {csv_file}")
            result = processor.process_file_in_batches(csv_file)
            logger.info(f"File: {os.path.basename(csv_file)}")
            logger.info(f"Total records: {result['total_records']}")
            logger.info(f"Successfully processed: {result['processed_records']}")
            logger.info(f"Failed records: {result['failed_records']}")
            
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise
    finally:
        processor.close()

if __name__ == "__main__":
    main()
