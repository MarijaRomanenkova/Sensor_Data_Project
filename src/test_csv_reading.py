import os
import time
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_processing.csv_processor import CSVProcessor

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

def test_csv_reading(num_records: int = 500000, num_runs: int = 3):
    """Test different CSV reading implementations."""
    test_file = "data/raw/test_csv_reading.csv"
    processor = CSVProcessor()
    results = {
        'sequential': [],
        'threaded': [],
        'parallel': []
    }
    
    try:
        # Generate test data once
        generate_test_data(num_records, test_file)
        
        # Test each method
        methods = [
            ('sequential', processor.read_csv_sequential),
            ('threaded', processor.read_csv_threaded),
            ('parallel', processor.read_csv_parallel)
        ]
        
        for method_name, method_func in methods:
            logger.info(f"\n=== Testing {method_name} reading ===")
            for i in range(num_runs):
                logger.info(f"Run {i + 1}/{num_runs}")
                result = method_func(test_file)
                results[method_name].append(result)
                
                logger.info(f"Records: {result['total_records']:,}")
                logger.info(f"Duration: {result['duration']:.2f} seconds")
                logger.info(f"Speed: {result['records_per_second']:,.2f} records/second")
        
        # Calculate and log average results
        logger.info("\n=== Average Results ===")
        for method_name in results:
            avg_duration = np.mean([r['duration'] for r in results[method_name]])
            avg_speed = np.mean([r['records_per_second'] for r in results[method_name]])
            logger.info(f"\n{method_name.capitalize()} Reading:")
            logger.info(f"Average Duration: {avg_duration:.2f} seconds")
            logger.info(f"Average Speed: {avg_speed:,.2f} records/second")
        
        # Save detailed results to file
        with open('csv_reading_results.txt', 'w') as f:
            f.write("=== CSV Reading Performance Test Results ===\n")
            f.write(f"Number of Records: {num_records:,}\n")
            f.write(f"Number of Runs: {num_runs}\n\n")
            
            for method_name in results:
                f.write(f"\n{method_name.capitalize()} Reading:\n")
                f.write("-" * 50 + "\n")
                for i, result in enumerate(results[method_name], 1):
                    f.write(f"Run {i}:\n")
                    f.write(f"  Duration: {result['duration']:.2f} seconds\n")
                    f.write(f"  Speed: {result['records_per_second']:,.2f} records/second\n")
                    f.write(f"  Chunks Processed: {result['chunks_processed']}\n")
                
                avg_duration = np.mean([r['duration'] for r in results[method_name]])
                avg_speed = np.mean([r['records_per_second'] for r in results[method_name]])
                f.write(f"\nAverage Results:\n")
                f.write(f"  Duration: {avg_duration:.2f} seconds\n")
                f.write(f"  Speed: {avg_speed:,.2f} records/second\n")
        
        return results
        
    finally:
        # Clean up test file
        if os.path.exists(test_file):
            os.remove(test_file)
            logger.info(f"Cleaned up test file: {test_file}")

if __name__ == "__main__":
    test_csv_reading() 
