import logging
import os

from data_processing.processor import DataProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    try:
        # Initialize data processor
        processor = DataProcessor()

        # Connect to MongoDB
        processor.connect_to_mongodb()

        # Process data files
        data_dir = os.path.join(os.getcwd(), "data", "raw")
        for filename in os.listdir(data_dir):
            if filename.endswith(".csv"):
                file_path = os.path.join(data_dir, filename)
                logger.info(f"Processing file: {filename}")

                # Process the file
                results = processor.process_file(file_path)

                # Log results
                logger.info(f"Processing results for {filename}:")
                logger.info(f"Total records: {results['total_records']}")
                logger.info(f"Processed records: {results['processed_records']}")
                logger.info(f"Failed records: {results['failed_records']}")

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise
    finally:
        # Close MongoDB connection
        if "processor" in locals():
            processor.close()


if __name__ == "__main__":
    main()
