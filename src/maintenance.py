import logging
from datetime import datetime, timedelta
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
        aggregated_data = processor.create_daily_aggregation()
        logger.info(f"Created {len(aggregated_data)} daily aggregations")
        
        # Clean up old data
        logger.info("Starting data cleanup...")
        processor.cleanup_old_data()
        
        # Get data quality metrics
        quality_metrics = processor.get_data_quality_metrics()
        logger.info("Data Quality Metrics:")
        logger.info(f"Total records: {quality_metrics['total_records']}")
        logger.info(f"Missing values: {quality_metrics['missing_values']}")
        logger.info(f"Out of range values: {quality_metrics['out_of_range']}")
        logger.info(f"Data quality score: {quality_metrics['data_quality_score']:.2f}%")
        
        # Get device statistics
        device_stats = processor.get_device_stats()
        logger.info(f"Active devices: {len(device_stats)}")
        
        # Get location statistics
        location_stats = processor.get_location_stats()
        logger.info(f"Active locations: {len(location_stats)}")
        
        logger.info("Maintenance tasks completed successfully")
        
    except Exception as e:
        logger.error(f"Error during maintenance: {str(e)}")
        raise
    finally:
        processor.close()

if __name__ == "__main__":
    run_maintenance() 
