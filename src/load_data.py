import os
import logging
from data_processing.processor import DataProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def load_data_from_csv(file_path: str):
    """Load data from a CSV file in batches."""
    processor = DataProcessor()
    
    try:
        # Connect to MongoDB
        processor.connect_to_mongodb()
        
        # Process the file in batches
        result = processor.process_file_in_batches(file_path)
        
        # Log the results
        logger.info(f"File: {os.path.basename(file_path)}")
        logger.info(f"Total records: {result['total_records']}")
        logger.info(f"Successfully processed: {result['processed_records']}")
        logger.info(f"Failed records: {result['failed_records']}")
        
    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
        raise
    finally:
        processor.close()

def main():
    # Path to your CSV files
    data_dir = "data/raw"
    csv_files = [
        os.path.join(data_dir, "real_time_data.csv")
    ]
    
    # Process each file
    for csv_file in csv_files:
        logger.info(f"Processing file: {csv_file}")
        load_data_from_csv(csv_file)
        logger.info(f"Finished processing: {csv_file}")

if __name__ == "__main__":
    main() 
