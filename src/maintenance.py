import logging
from data_processing.processor import DataProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def run_maintenance():
    """Run daily maintenance tasks."""
    processor = DataProcessor()
    
    try:
        # Connect to MongoDB
        processor.connect_to_mongodb()
        
        # Create daily aggregation
        logger.info("Starting daily aggregation...")
        processor.create_daily_aggregation()
        
        # Clean up old data
        logger.info("Starting data cleanup...")
        processor.cleanup_old_data()
        
        logger.info("Maintenance tasks completed successfully")
        
    except Exception as e:
        logger.error(f"Error during maintenance: {str(e)}")
        raise
    finally:
        processor.close()

if __name__ == "__main__":
    run_maintenance() 
