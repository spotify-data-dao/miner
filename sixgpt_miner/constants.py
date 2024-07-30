import os

BASE_NAME='sixgpt'
TMP_DIR_BASE = os.path.expanduser(f"~/.{BASE_NAME}")

TMP_MINER_LOG = f"{TMP_DIR_BASE}/miner.log"
TMP_PID_FILE = f"{TMP_DIR_BASE}/miner.pid"
TMP_TWITTER_AUTH = f"{TMP_DIR_BASE}/twitter.cookies"
TMP_DRIVE_AUTH = f"{TMP_DIR_BASE}/drive.token"

TIMELINE_SLEEP_INTERVAL = 120
TARGET_TWEET_COUNT = 1000

API_URL = "https://serve.sixgpt.xyz"
DLP_ADDRESS = "0x000000000000000000000000000000"
