import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB settings
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://admin:password123@mongodb:27017/")
MONGODB_DB = os.getenv("MONGODB_DB", "sensor_data")
MONGODB_COLLECTION = "sensor_readings"

# Data processing settings
BATCH_SIZE = 50000  # Optimized for high throughput processing
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
