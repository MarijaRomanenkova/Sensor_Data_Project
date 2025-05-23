# Performance Test & Proof of System Capability

## Overview
This document describes the performance test conducted to demonstrate that the data processing system can efficiently handle and process **500,000 environmental sensor records** in batches. The test provides concrete evidence of the system's scalability, speed, and data quality.

---

## Test Location & Key Files
- **Test Script:** [`src/test_performance.py`](../src/test_performance.py)
- **Batch Processing Logic:** [`src/data_processing/processor.py`](../src/data_processing/processor.py)
- **Batch Size Setting:** [`src/config/settings.py`](../src/config/settings.py)
- **Docker Setup:** [`docker-compose.yml`](../docker-compose.yml), [`docker/Dockerfile`](../docker/Dockerfile)

---

## How the Test Dataset Was Created
The test script automatically generates a synthetic dataset of 500,000 records with realistic sensor data fields:
- **Timestamp:** Spanning 30 days
- **Device ID:** 50 unique devices
- **Temperature, Humidity, Pressure, Light, Sound, Motion, Battery, Location:** Randomized within realistic ranges

**Relevant code:** See `generate_test_data` in [`src/test_performance.py`](../src/test_performance.py):
```python
# src/test_performance.py
def generate_test_data(num_records: int, output_file: str):
    ...
    # Generates 500,000 records with realistic values and saves to CSV
```
The generated CSV is saved to `data/raw/test_large_dataset.csv`.

---

## How the Test Was Run
The test is run as a dedicated Docker Compose service:
- **Service definition:** See `test` service in [`docker-compose.yml`](../docker-compose.yml)
- **Command:**
  ```bash
  docker compose run test
  ```
- The test script:
  1. Connects to MongoDB
  2. Generates the dataset
  3. Processes the file in batches of 50,000 records (see [`BATCH_SIZE` in settings](../src/config/settings.py))
  4. Inserts records into MongoDB
  5. Logs performance and data quality metrics

---

## Proof of Capability: Results
**Summary from logs:**
- **Total records processed:** 500,000
- **Batch size:** 50,000 (10 batches)
- **Processing time:** 21.13 seconds (file processing), 23.19 seconds (total)
- **Average speed:** ~21,559 records/second
- **Memory usage:** 186.33 MB
- **Failed records:** 0
- **Success rate:** 100%
- **Data quality score:** 100%
- **Missing values:** 0
- **Out of range values:** 0

**Explanation of Metrics:**
These metrics are logged by the test script (`src/test_performance.py`) during execution. The script:
- Calculates total processing time and speed based on start/end timestamps.
- Uses `psutil` to measure memory usage.
- Tracks failed records and success rate from the batch processing logic in `src/data_processing/processor.py`.
- Computes data quality metrics (missing values, out-of-range values) using the `get_data_quality_metrics` method in the processor.

**Sample log output:**
```
=== Performance Test Results ===
Total time: 23.19 seconds
Total records processed: 500,000
Processing speed: 21,558.87 records/second
Failed records: 0
Success rate: 100.00%
Memory usage: 186.33 MB

=== Data Quality Metrics ===
Data quality score: 100.00%
Missing values: 0
Out of range values: 0
```

---

## Conclusion
This test provides concrete, reproducible proof that the system can efficiently process and store 500,000 records in batches, with:
- High throughput
- Low memory usage
- Perfect data quality

All code, configuration, and test logic are available in the referenced files for review or reproduction. 
