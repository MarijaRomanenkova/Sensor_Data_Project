import pytest
import pandas as pd
from datetime import datetime, timedelta
from src.data_processing.processor import DataProcessor
from pymongo.errors import PyMongoError
from mongomock import MongoClient
from config.settings import BATCH_SIZE

@pytest.fixture
def sample_data():
    return pd.DataFrame({
        'timestamp': [datetime.now()],
        'device_id': ['test_device'],
        'temperature': [25.0],
        'humidity': [50.0],
        'pressure': [1013.0],
        'location': ['test_location']
    })

@pytest.fixture
def mock_mongodb(mocker):
    # Mock MongoDB client and collections
    mock_client = mocker.Mock()
    mock_db = mocker.Mock()
    mock_collection = mocker.Mock()
    mock_aggregated_collection = mocker.Mock()
    
    mock_client.__getitem__.return_value = mock_db
    mock_db.__getitem__.side_effect = lambda x: mock_collection if x == "sensor_readings" else mock_aggregated_collection
    
    return mock_client, mock_db, mock_collection, mock_aggregated_collection

@pytest.fixture
def processor(mock_mongodb):
    client, db, collection, aggregated_collection = mock_mongodb
    processor = DataProcessor()
    processor.client = client
    processor.db = db
    processor.collection = collection
    processor.aggregated_collection = aggregated_collection
    return processor

def test_initialization(processor):
    assert processor is not None
    assert isinstance(processor, DataProcessor)
    assert processor.batch_size == BATCH_SIZE

def test_process_batch(processor, sample_data):
    records = sample_data.to_dict('records')
    result = processor.process_batch(records)
    assert isinstance(result, int)
    assert result > 0

def test_validate_data(processor, sample_data):
    record = sample_data.iloc[0].to_dict()
    assert processor.validate_data(record) is True

def test_validate_data_invalid_types(processor):
    invalid_data = {
        'timestamp': 123,  # Should be string or datetime
        'device_id': 456,  # Should be string
        'temperature': 'hot',  # Should be number
        'humidity': 'wet',  # Should be number
        'pressure': 'high',  # Should be number
        'light': 'bright',  # Should be number
        'sound': 'loud',  # Should be number
        'motion': 'active',  # Should be boolean
        'battery': 'full',  # Should be number
        'location': 'unknown'  # Should be string
    }
    assert processor.validate_data(invalid_data) is False

def test_validate_data_out_of_range(processor):
    out_of_range_data = {
        'timestamp': '2024-01-01',
        'device_id': 'Device_1',
        'temperature': 100,  # Out of range
        'humidity': 150,  # Out of range
        'pressure': 1100,  # Out of range
        'light': 1000,  # Out of range
        'sound': 100,  # Out of range
        'motion': 2,  # Out of range
        'battery': 100.5,  # Out of range
        'location': 'Room Z'  # Out of range
    }
    assert processor.validate_data(out_of_range_data) is False

def test_data_quality_metrics(processor):
    # Add some test data first
    test_data = {
        'timestamp': datetime.utcnow(),
        'device_id': 'Device_1',
        'temperature': 25.0,
        'humidity': 50.0,
        'pressure': 1013.2,
        'light': 500,
        'sound': 45,
        'motion': 0,
        'battery': 95.5,
        'location': 'Room A'
    }
    processor.collection.insert_one(test_data)
    
    metrics = processor.get_data_quality_metrics()
    assert isinstance(metrics, dict)
    assert 'total_records' in metrics
    assert 'missing_values' in metrics
    assert 'out_of_range' in metrics
    assert 'data_quality_score' in metrics

def test_backup_database(processor, tmp_path):
    # Add some test data first
    test_data = {
        'timestamp': datetime.utcnow(),
        'device_id': 'Device_1',
        'temperature': 25.0,
        'humidity': 50.0,
        'pressure': 1013.2,
        'light': 500,
        'sound': 45,
        'motion': 0,
        'battery': 95.5,
        'location': 'Room A'
    }
    processor.collection.insert_one(test_data)
    
    backup_path = str(tmp_path)
    processor.backup_database(backup_path)
    # Check if backup files were created
    backup_files = list(tmp_path.glob('*.json'))
    assert len(backup_files) > 0

def test_cleanup_old_data(processor):
    # Add some old data
    old_date = datetime.utcnow() - timedelta(days=400)  # More than 1 year old
    processor.collection.insert_one({
        'timestamp': old_date,
        'device_id': 'Device_1',
        'temperature': 25.0,
        'humidity': 50.0,
        'pressure': 1013.2,
        'light': 500,
        'sound': 45,
        'motion': 0,
        'battery': 95.5,
        'location': 'Room A'
    })
    
    # Run cleanup
    processor.cleanup_old_data()
    
    # Check if old data was removed
    old_data = processor.collection.find_one({'timestamp': old_date})
    assert old_data is None

def test_create_daily_aggregation(processor):
    # Add some test data
    test_date = datetime.utcnow() - timedelta(days=1)
    processor.collection.insert_many([
        {
            'timestamp': test_date,
            'device_id': 'Device_1',
            'temperature': 25.0,
            'humidity': 50.0,
            'pressure': 1013.2,
            'light': 500,
            'sound': 45,
            'motion': 0,
            'battery': 95.5,
            'location': 'Room A'
        },
        {
            'timestamp': test_date,
            'device_id': 'Device_1',
            'temperature': 26.0,
            'humidity': 51.0,
            'pressure': 1013.5,
            'light': 550,
            'sound': 50,
            'motion': 1,
            'battery': 95.0,
            'location': 'Room A'
        }
    ])
    
    # Create aggregation and get results
    aggregated_data = processor.create_daily_aggregation()
    assert aggregated_data is not None
    assert len(aggregated_data) > 0
    
    # Find the aggregation for Device_1
    device1_aggregation = next((item for item in aggregated_data if item['device_id'] == 'Device_1'), None)
    assert device1_aggregation is not None
    assert 'avg_temperature' in device1_aggregation
    assert 'avg_humidity' in device1_aggregation
    assert 'avg_pressure' in device1_aggregation
    
    # Verify the aggregated values using pytest.approx for floating-point comparison
    assert device1_aggregation['avg_temperature'] == pytest.approx(25.5)  # (25.0 + 26.0) / 2
    assert device1_aggregation['avg_humidity'] == pytest.approx(50.5)  # (50.0 + 51.0) / 2
    assert device1_aggregation['avg_pressure'] == pytest.approx(1013.35)  # (1013.2 + 1013.5) / 2

def test_mongodb_connection(processor):
    """Test that MongoDB connection is working properly."""
    try:
        # Try to ping the database
        processor.client.admin.command('ping')
        assert processor.client is not None
        assert processor.db is not None
        assert processor.collection is not None
        assert processor.aggregated_collection is not None
    except PyMongoError as e:
        pytest.fail(f"MongoDB connection test failed: {str(e)}")
