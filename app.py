import os
import requests
from flask import Flask, request

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
INSTAGRAM_USER_ID = os.environ.get("INSTAGRAM_USER_ID")

GRAPH_VERSION = "v23.0"


@app.route("/", methods=["GET"])
def home():
    return "ZELVÉN BOT is running!", 200


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200

    return "Verification failed", 403


@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json(silent=True)

    if not data:
        return "OK", 200

    try:
        for entry in data.get("entry", []):
            for messaging in entry.get("messaging", []):

                sender = messaging.get("sender", {})
                sender_id = sender.get("id")

                message = messaging.get("message", {})
                text = message.get("text", "")

                if sender_id and text:
                    reply = create_reply(text)
                    send_message(sender_id, reply)

    except Exception as e:
        print("Webhook error:", e)

    return "OK", 200


def create_reply(text):
    text = text.lower().strip()

    if any(word in text for word in ["سلام", "السلام", "مرحبا", "اهلا", "أهلا"]):
        return (
            "وعليكم السلام 🌸 أهلاً بك في ZELVÉN PARFUMS!\n\n"
            "كيف يمكننا مساعدتك؟\n"
            "🌹 العطور\n"
            "💰 الأسعار\n"
            "📦 التوصيل\n"
            "🛍️ الطلب"
        )

    if any(word in text for word in ["سعر", "ثمن", "كم", "prix", "price"]):
        return (
            "مرحباً بك في ZELVÉN PARFUMS ✨\n\n"
            "أرسل لنا اسم العطر الذي ترغب فيه وسنخبرك بالسعر والتوفر."
        )

    if any(word in text for word in ["توصيل", "delivery", "livraison"]):
        return (
            "نعم، نوفر التوصيل 📦✨\n"
            "أرسل لنا مدينتك وسنخبرك بتفاصيل التوصيل."
        )

    return (
        "أهلاً بك في ZELVÉN PARFUMS 🌹\n\n"
        "شكراً لتواصلك معنا.\n"
        "اكتب اسم العطر أو اسأل عن السعر، التوصيل أو الطلب."
    )


def send_message(recipient_id, text):
    url = f"https://graph.instagram.com/{GRAPH_VERSION}/me/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": text
        }
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=20
    )

    print("Instagram API:", response.status_code, response.text)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
