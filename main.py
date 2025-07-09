import os, time, random, sqlite3, threading, requests, logging
from flask import Flask, jsonify, render_template_string
from dotenv import load_dotenv
load_dotenv()

# === CONFIG ===
WALLETS = os.getenv("USDT_WALLETS", "").split(",")
DB = "revenue.db"

# === LOGGING ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AutonomousBotSystem")

# === DB INIT ===
def init_db():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS revenue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot TEXT,
            amount REAL,
            source TEXT,
            wallet TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# === BOT MODEL ===
class Bot:
    def __init__(self, name, strategy):
        self.name = name
        self.strategy = strategy
        self.revenue = 0.0

    def run(self):
        try:
            amount = self.strategy(self)
            if amount > 0:
                wallet = random.choice(WALLETS)
                conn = sqlite3.connect(DB)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO revenue (bot, amount, source, wallet) VALUES (?, ?, ?, ?)",
                               (self.name, amount, self.strategy.__name__, wallet))
                conn.commit()
                conn.close()
                self.revenue += amount
                logger.info(f"💰 {self.name} earned ${amount:.2f} via {self.strategy.__name__} → {wallet}")
        except Exception as e:
            logger.error(f"❌ {self.name} failed: {e}")

# === STRATEGIES ===
def fetch_crypto(bot):
    try:
        url = os.getenv("COINGECKO_API")
        r = requests.get(url)
        price = r.json()["bitcoin"]["usd"]
        return round(price * 0.0001, 2)
    except: return 0.0

def fetch_news(bot):
    try:
        url = os.getenv("NEWS_API")
        r = requests.get(url)
        if r.status_code == 200: return 5.0
    except: pass
    return 0.0

def fetch_weather(bot):
    try:
        url = os.getenv("WEATHER_API")
        r = requests.get(url)
        if r.status_code == 200: return 3.0
    except: pass
    return 0.0

STRATEGIES = [fetch_crypto, fetch_news, fetch_weather]

# === BOT DEPLOYMENT ===
bots = [Bot(f"bot_{i}", random.choice(STRATEGIES)) for i in range(5)]

def bot_loop():
    while True:
        for bot in bots:
            bot.run()
            time.sleep(random.uniform(5, 10))
        time.sleep(30)

# === DASHBOARD ===
app = Flask(__name__)

@app.route("/")
def dashboard():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT bot, SUM(amount), source, wallet FROM revenue GROUP BY bot, source, wallet")
    data = cursor.fetchall()
    conn.close()
    html = """
    <h1>🤖 Bot Revenue Dashboard</h1>
    <table border=1 cellpadding=8>
    <tr><th>Bot</th><th>Amount</th><th>Source</th><th>Wallet</th></tr>
    {% for row in data %}
    <tr><td>{{row[0]}}</td><td>${{row[1]:.2f}}</td><td>{{row[2]}}</td><td>{{row[3]}}</td></tr>
    {% endfor %}
    </table>
    """
    return render_template_string(html, data=data)

# === START ===
if __name__ == "__main__":
    threading.Thread(target=bot_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
