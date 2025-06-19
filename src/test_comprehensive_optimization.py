import os
import time
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from data_processing.processor import DataProcessor
from config import settings
import psutil
from itertools import product
import threading
import time as time_module

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
        'device_id': [f'Device_{i % 50 + 1}' for i in range(num_records)],
        'temperature': np.random.uniform(-10, 40, num_records).round(2),
        'humidity': np.random.uniform(0, 100, num_records).round(2),
        'pressure': np.random.uniform(800, 1200, num_records).round(2),
        'light': np.random.randint(0, 1000, num_records),
        'sound': np.random.randint(0, 100, num_records),
        'motion': np.random.randint(0, 2, num_records),
        'battery': np.random.uniform(0, 100, num_records).round(2),
        'location': [f'Location_{i % 10 + 1}' for i in range(num_records)]
    }
    
    # Create DataFrame and save to CSV
    df = pd.DataFrame(data)
    df.to_csv(output_file, index=False)
    logger.info(f"Test dataset saved to {output_file}")
    return df

def test_comprehensive_optimization():
    """Test all pipeline parameters to find optimal configuration."""
    
    # Generate test data
    test_file = "data/raw/test_comprehensive.csv"
    generate_test_data(500000, test_file)
    
    # Define parameter ranges to test
    param_ranges = {
        'CHUNK_SIZE': [1000, 5000, 10000],  # CSV reading chunk size
        'VALIDATION_CHUNK_SIZE': [250, 500, 1000],  # Validation chunk size
        'MONGODB_INSERT_BATCH_SIZE': [250, 500, 1000, 2000],  # MongoDB insert batch size
        'MAX_WORKERS': [2, 4, 8],  # Number of worker threads
        'MONGODB_POOL_SIZE': [5, 10],  # Connection pool min size
        'MONGODB_MAX_POOL_SIZE': [25, 50]  # Connection pool max size
    }
    
    # Generate all combinations (but limit to most promising ones to avoid too many tests)
    # We'll test a subset of combinations that are most likely to be optimal
    test_configs = [
        # (CHUNK_SIZE, VALIDATION_CHUNK_SIZE, INSERT_BATCH_SIZE, MAX_WORKERS, POOL_SIZE, MAX_POOL_SIZE)
        # Conservative configurations
        (1000, 250, 250, 2, 5, 25),
        (1000, 500, 500, 2, 5, 25),
        (1000, 1000, 1000, 2, 5, 25),
        (5000, 250, 250, 2, 5, 25),
        (5000, 500, 500, 2, 5, 25),
        (5000, 1000, 1000, 2, 5, 25),
        (10000, 250, 250, 2, 5, 25),
        (10000, 500, 500, 2, 5, 25),
        (10000, 1000, 1000, 2, 5, 25),
        
        # Medium configurations
        (1000, 500, 500, 4, 5, 25),
        (1000, 1000, 1000, 4, 5, 25),
        (5000, 500, 500, 4, 5, 25),
        (5000, 1000, 1000, 4, 5, 25),
        (10000, 500, 500, 4, 5, 25),
        (10000, 1000, 1000, 4, 5, 25),
        
        # Aggressive configurations
        (1000, 1000, 2000, 4, 5, 25),
        (5000, 1000, 2000, 4, 5, 25),
        (10000, 1000, 2000, 4, 5, 25),
        (10000, 500, 1000, 8, 5, 25),
        (10000, 1000, 2000, 8, 5, 25),
        
        # High worker configurations
        (10000, 500, 500, 8, 10, 50),
        (10000, 1000, 1000, 8, 10, 50),
        (10000, 1000, 2000, 8, 10, 50),
    ]
    
    results = []
    total_tests = len(test_configs)
    
    logger.info(f"\nStarting comprehensive optimization test with {total_tests} configurations...")
    
    # Temporarily reduce logging level for processor (same as performance test)
    processor_logger = logging.getLogger('data_processing.processor')
    original_level = processor_logger.level
    processor_logger.setLevel(logging.WARNING)
    
    try:
        for i, (chunk_size, validation_chunk_size, insert_batch_size, max_workers, pool_size, max_pool_size) in enumerate(test_configs, 1):
            logger.info(f"\n=== Test {i}/{total_tests}: CHUNK={chunk_size}, VAL={validation_chunk_size}, INSERT={insert_batch_size}, WORKERS={max_workers}, POOL={pool_size}-{max_pool_size} ===")
            
            # Run each configuration 3 times
            run_results = []
            
            for run in range(3):
                logger.info(f"  Run {run + 1}/3...")
                
                try:
                    # Update all settings
                    settings.CHUNK_SIZE = chunk_size
                    settings.VALIDATION_CHUNK_SIZE = validation_chunk_size
                    settings.MONGODB_INSERT_BATCH_SIZE = insert_batch_size
                    settings.MAX_WORKERS = max_workers
                    settings.MONGODB_POOL_SIZE = pool_size
                    settings.MONGODB_MAX_POOL_SIZE = max_pool_size
                    
                    # Create processor with updated settings
                    processor = DataProcessor()
                    
                    # Connect to MongoDB
                    processor.mongo_uri = settings.MONGODB_URI
                    processor.db_name = settings.MONGODB_DB + "_comprehensive_test"
                    processor.connect_to_mongodb()
                    
                    # Clean up existing data
                    processor.collection.delete_many({})
                    
                    # Get initial memory
                    process = psutil.Process()
                    initial_memory = process.memory_info().rss / 1024 / 1024
                    
                    # Track memory during processing
                    memory_samples = []
                    
                    # Measure performance
                    start_time = time.time()
                    
                    # Start memory monitoring in a separate thread
                    def monitor_memory():
                        while hasattr(monitor_memory, 'running') and monitor_memory.running:
                            try:
                                current_memory = process.memory_info().rss / 1024 / 1024
                                memory_samples.append(current_memory)
                                time_module.sleep(0.1)  # Sample every 100ms
                            except:
                                break
                    
                    monitor_memory.running = True
                    memory_thread = threading.Thread(target=monitor_memory)
                    memory_thread.daemon = True
                    memory_thread.start()
                    
                    result = processor.process_file_in_batches(test_file)
                    
                    # Stop memory monitoring
                    monitor_memory.running = False
                    memory_thread.join(timeout=1)
                    
                    end_time = time.time()
                    
                    # Calculate metrics
                    duration = end_time - start_time
                    final_memory = process.memory_info().rss / 1024 / 1024
                    peak_memory = max(memory_samples) if memory_samples else final_memory
                    avg_memory = np.mean(memory_samples) if memory_samples else final_memory
                    memory_used = peak_memory - initial_memory
                    records_per_second = result['processed_records'] / duration if duration > 0 else 0
                    
                    run_results.append({
                        'duration': duration,
                        'records_per_second': records_per_second,
                        'memory_used': memory_used,
                        'peak_memory': peak_memory,
                        'avg_memory': avg_memory,
                        'processed_records': result['processed_records'],
                        'failed_records': result['failed_records']
                    })
                    
                    processor.close()
                    
                except Exception as e:
                    logger.error(f"  Error in run {run + 1}: {str(e)}")
                    run_results.append({
                        'duration': 0,
                        'records_per_second': 0,
                        'memory_used': 0,
                        'peak_memory': 0,
                        'avg_memory': 0,
                        'processed_records': 0,
                        'failed_records': 0,
                        'error': str(e)
                    })
            
            # Calculate averages for this configuration
            successful_runs = [r for r in run_results if 'error' not in r]
            
            if successful_runs:
                avg_duration = np.mean([r['duration'] for r in successful_runs])
                avg_speed = np.mean([r['records_per_second'] for r in successful_runs])
                avg_memory = np.mean([r['memory_used'] for r in successful_runs])
                avg_peak_memory = np.mean([r['peak_memory'] for r in successful_runs])
                avg_avg_memory = np.mean([r['avg_memory'] for r in successful_runs])
                std_duration = np.std([r['duration'] for r in successful_runs])
                std_speed = np.std([r['records_per_second'] for r in successful_runs])
                std_memory = np.std([r['memory_used'] for r in successful_runs])
                std_peak_memory = np.std([r['peak_memory'] for r in successful_runs])
                std_avg_memory = np.std([r['avg_memory'] for r in successful_runs])
                
                results.append({
                    'chunk_size': chunk_size,
                    'validation_chunk_size': validation_chunk_size,
                    'insert_batch_size': insert_batch_size,
                    'max_workers': max_workers,
                    'pool_size': pool_size,
                    'max_pool_size': max_pool_size,
                    'duration': avg_duration,
                    'duration_std': std_duration,
                    'records_per_second': avg_speed,
                    'speed_std': std_speed,
                    'memory_used': avg_memory,
                    'memory_std': std_memory,
                    'peak_memory': avg_peak_memory,
                    'peak_memory_std': std_peak_memory,
                    'avg_memory': avg_avg_memory,
                    'avg_memory_std': std_avg_memory,
                    'successful_runs': len(successful_runs),
                    'total_runs': len(run_results)
                })
                
                logger.info(f"  Results (avg of {len(successful_runs)} runs):")
                logger.info(f"    Processing Time: {avg_duration:.2f} ± {std_duration:.2f} seconds")
                logger.info(f"    Processing Speed: {avg_speed:,.2f} ± {std_speed:,.2f} records/second")
                logger.info(f"    Peak Memory: {avg_peak_memory:.2f} ± {std_peak_memory:.2f} MB")
                logger.info(f"    Avg Memory: {avg_avg_memory:.2f} ± {std_avg_memory:.2f} MB")
                logger.info(f"    Processed Records: {successful_runs[0]['processed_records']:,}")
                logger.info(f"    Failed Records: {successful_runs[0]['failed_records']:,}")
            else:
                logger.error(f"  All runs failed for this configuration")
    
    finally:
        # Restore original logging level
        processor_logger.setLevel(original_level)
        
        # Clean up test file
        try:
            if os.path.exists(test_file):
                os.remove(test_file)
                logger.info(f"Cleaned up test file: {test_file}")
        except Exception as e:
            logger.error(f"Error cleaning up test file: {str(e)}")

    return results

if __name__ == "__main__":
    test_comprehensive_optimization() 
