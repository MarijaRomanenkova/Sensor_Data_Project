import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB settings
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB = os.getenv("MONGODB_DB", "sensor_data")
MONGODB_COLLECTION = "sensor_readings"

# MongoDB connection pooling settings
MONGODB_POOL_SIZE = 5  # Minimum pool size
MONGODB_MAX_POOL_SIZE = 25  # Maximum pool size
MONGODB_WAIT_QUEUE_TIMEOUT_MS = 500  # Wait queue timeout
MONGODB_MAX_IDLE_TIME_MS = 15000  # Max idle time for connections
MONGODB_CONNECT_TIMEOUT_MS = 30000  # Connection timeout
MONGODB_SOCKET_TIMEOUT_MS = 30000  # Socket timeout

# MongoDB write concern settings
MONGODB_WRITE_CONCERN_W = 1  # Write acknowledgment level (0=no ack, 1=primary, majority=majority)
MONGODB_WRITE_CONCERN_J = False  # Journal acknowledgment
MONGODB_WRITE_CONCERN_WTIMEOUT = 5000  # Write timeout in milliseconds

# Data processing settings
BATCH_SIZE = 2000  # For MongoDB write operations
CHUNK_SIZE = 1000  # For CSV reading operations
VALIDATION_CHUNK_SIZE = 1000  # For validation operations
MAX_WORKERS = 4  # Number of worker threads for parallel processing
MONGODB_INSERT_BATCH_SIZE = 2000  # Fixed batch size for MongoDB insertion (for testing)
DATA_DIR = os.path.join(os.getcwd(), "data", "raw")

# Data validation ranges
TEMPERATURE_RANGE = (-50, 50)  # Celsius
HUMIDITY_RANGE = (0, 100)  # Percentage
PRESSURE_RANGE = (800, 1200)  # hPa
LIGHT_RANGE = (0, None)  # Minimum 0, no maximum
SOUND_RANGE = (0, None)  # Minimum 0, no maximum
MOTION_RANGE = (0, 1)  # Binary
BATTERY_RANGE = (0, 100)  # Percentage

# Logging settings
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL = "INFO"
