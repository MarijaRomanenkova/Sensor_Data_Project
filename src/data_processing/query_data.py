from processor import DataProcessor
import json
from datetime import datetime, timedelta

def print_results(results):
    """Pretty print the results."""
    print(json.dumps(results, indent=2))

def main():
    # Initialize the processor
    processor = DataProcessor()
    processor.connect_to_mongodb()

    try:
        # Example 1: Get the last 5 readings for a specific device
        print("\n=== Last 5 readings for Device_21 ===")
        device_readings = processor.query_data(
            query={"device_id": "Device_21"},
            limit=5,
            sort_by="timestamp",
            sort_order=-1  # -1 for descending (newest first)
        )
        print_results(device_readings)

        # Example 2: Get statistics for a specific device
        print("\n=== Statistics for Device_21 ===")
        device_stats = processor.get_device_stats("Device_21")
        print_results(device_stats)

        # Example 3: Get readings within a temperature range
        print("\n=== Readings with temperature between 25 and 30 degrees ===")
        temp_readings = processor.query_data(
            query={"temperature": {"$gt": 25, "$lt": 30}},
            limit=5
        )
        print_results(temp_readings)

        # Example 4: Get readings from a specific location
        print("\n=== Readings from Room A ===")
        location_readings = processor.query_data(
            query={"location": "Room A"},
            limit=5
        )
        print_results(location_readings)

        # Example 5: Get statistics for all locations
        print("\n=== Statistics for all locations ===")
        location_stats = processor.get_location_stats()
        print_results(location_stats)

        # Example 6: Get readings from the last hour
        one_hour_ago = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        print("\n=== Readings from the last hour ===")
        recent_readings = processor.query_data(
            query={"timestamp": {"$gt": one_hour_ago}},
            limit=5,
            sort_by="timestamp",
            sort_order=-1
        )
        print_results(recent_readings)

    finally:
        # Always close the connection when done
        processor.close()

if __name__ == "__main__":
    main() 
