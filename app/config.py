import os

from dotenv import load_dotenv

load_dotenv()

API_KEY_INDEX = 2
BASE_URL = "https://mainnet.zklighter.elliot.ai"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

AGENT_INTERVAL_SECONDS = 60 * 5
PRICE_TRACKER_INTERVAL_SECONDS = 60 * 2
SERVER_PORT = 3000
