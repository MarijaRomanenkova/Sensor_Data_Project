import logging
from data_processing.processor import DataProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def check_records():
    processor = DataProcessor()
    
    try:
        # Connect to MongoDB
        processor.connect_to_mongodb()
        
        # Get total number of records
        total_records = processor.collection.count_documents({})
        logger.info(f"Total number of records in database: {total_records}")
        
        # Get number of unique devices
        unique_devices = len(processor.collection.distinct("device_id"))
        logger.info(f"Number of unique devices: {unique_devices}")
        
        # Get number of unique locations
        unique_locations = len(processor.collection.distinct("location"))
        logger.info(f"Number of unique locations: {unique_locations}")
        
        # Get date range
        first_record = processor.collection.find_one(sort=[("timestamp", 1)])
        last_record = processor.collection.find_one(sort=[("timestamp", -1)])
        
        if first_record and last_record:
            logger.info(f"Data range: from {first_record['timestamp']} to {last_record['timestamp']}")
        
    except Exception as e:
        logger.error(f"Error checking records: {str(e)}")
        raise
    finally:
        processor.close()

if __name__ == "__main__":
    check_records() 
