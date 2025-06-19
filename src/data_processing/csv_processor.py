import logging
import pandas as pd
import time
from typing import Dict, Any, List, Generator
import threading
import queue
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class CSVProcessor:
    def __init__(self, chunk_size: int = 10000):
        self.chunk_size = chunk_size
        self.max_workers = 4  # Number of worker threads

    def read_csv_sequential(self, file_path: str) -> Dict[str, Any]:
        """Read CSV file sequentially using pandas chunks."""
        start_time = time.time()
        total_records = 0
        chunks_processed = 0
        
        try:
            for chunk in pd.read_csv(
                file_path,
                chunksize=self.chunk_size,
                parse_dates=['timestamp'],
                infer_datetime_format=True,
                low_memory=False
            ):
                total_records += len(chunk)
                chunks_processed += 1
                
            duration = time.time() - start_time
            return {
                'method': 'sequential',
                'total_records': total_records,
                'chunks_processed': chunks_processed,
                'duration': duration,
                'records_per_second': total_records / duration if duration > 0 else 0
            }
        except Exception as e:
            logger.error(f"Error in sequential reading: {str(e)}")
            raise

    def read_csv_threaded(self, file_path: str) -> Dict[str, Any]:
        """Read CSV file using a threaded approach with a queue."""
        start_time = time.time()
        total_records = 0
        chunks_processed = 0
        chunk_queue = queue.Queue(maxsize=10)  # Buffer 10 chunks
        
        def read_chunks():
            try:
                for chunk in pd.read_csv(
                    file_path,
                    chunksize=self.chunk_size,
                    parse_dates=['timestamp'],
                    infer_datetime_format=True,
                    low_memory=False
                ):
                    chunk_queue.put(chunk)
                chunk_queue.put(None)  # Signal end
            except Exception as e:
                logger.error(f"Error in reader thread: {str(e)}")
                chunk_queue.put(None)  # Signal error
        
        # Start reader thread
        reader_thread = threading.Thread(target=read_chunks)
        reader_thread.start()
        
        # Process chunks as they become available
        while True:
            chunk = chunk_queue.get()
            if chunk is None:
                break
            total_records += len(chunk)
            chunks_processed += 1
        
        duration = time.time() - start_time
        return {
            'method': 'threaded',
            'total_records': total_records,
            'chunks_processed': chunks_processed,
            'duration': duration,
            'records_per_second': total_records / duration if duration > 0 else 0
        }

    def read_csv_parallel(self, file_path: str) -> Dict[str, Any]:
        """Read CSV file using parallel processing with ThreadPoolExecutor."""
        start_time = time.time()
        total_records = 0
        chunks_processed = 0
        
        def process_chunk(chunk):
            return len(chunk)
        
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = []
                for chunk in pd.read_csv(
                    file_path,
                    chunksize=self.chunk_size,
                    parse_dates=['timestamp'],
                    infer_datetime_format=True,
                    low_memory=False
                ):
                    future = executor.submit(process_chunk, chunk)
                    futures.append(future)
                    chunks_processed += 1
                
                # Collect results
                for future in futures:
                    total_records += future.result()
            
            duration = time.time() - start_time
            return {
                'method': 'parallel',
                'total_records': total_records,
                'chunks_processed': chunks_processed,
                'duration': duration,
                'records_per_second': total_records / duration if duration > 0 else 0
            }
        except Exception as e:
            logger.error(f"Error in parallel reading: {str(e)}")
            raise 
