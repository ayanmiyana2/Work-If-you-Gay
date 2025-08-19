from flask import Flask, request
import telegram
import threading
import time
import json
import os
from config import BOT_TOKEN, ADMIN_ID
from bot_commands import handle_update

app = Flask(__name__)
bot = telegram.Bot(token=BOT_TOKEN)

DATA_FILE = "data.json"
LOCK = threading.Lock()

# Load or initialize data
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
else:
    data = {
        "users": {},        # user_id: {is_premium, redeem_count, keys_used, points, accounts_taken}
        "keys": {},         # key: {"days":int, "used":False}
        "banned": [],       # user ids
        "free_service": False,
        "accounts": {},     # acc_id: {"email":..., "password":..., "service":..., "assigned_to":[user_id1,user_id2]}
        "orders": {},       # order_id: {"user_id":..., "status":"pending/approved/failed"}
    }

def save_data():
    with LOCK:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=2)

@app.route('/', methods=["GET"])
def index():
    return "Bot is running..."

@app.route('/poll', methods=['POST'])
def poll():
    # Telegram updates via polling from Render or manual calls, no webhook
    update_json = request.get_json()
    threading.Thread(target=handle_update, args=(bot, update_json, data, save_data, LOCK)).start()
    return "ok"

if __name__ == "__main__":
    # Run Flask app
    app.run(threaded=True, host='0.0.0.0', port=5000)
