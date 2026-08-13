import os
import re
import json
import time
import hmac
import hashlib
import sqlite3
import threading

import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from google import genai

# =========================================================
# ZELVÉN AI BOT
# Instagram + Gemini + Memory + Products + Orders
# Vercel / Flask
# =========================================================

load_dotenv()

# مهم جدًا لـ Vercel:
app = Flask(__name__)

# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

INSTAGRAM_ACCESS_TOKEN = os.getenv(
    "INSTAGRAM_ACCESS_TOKEN",
    ""
).strip()

VERIFY_TOKEN = os.getenv(
    "VERIFY_TOKEN",
    "zelven_verify_2026"
).strip()

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    ""
).strip()

META_APP_SECRET = os.getenv(
    "META_APP_SECRET",
    ""
).strip()

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash"
)

WHATSAPP_NUMBER = os.getenv(
    "WHATSAPP_NUMBER",
    "212649982831"
)

# =========================================================
# GEMINI
# =========================================================

gemini = None

if GEMINI_API_KEY:
    try:
        gemini = genai.Client(
            api_key=GEMINI_API_KEY
        )
    except Exception as e:
        print("Gemini initialization error:", repr(e))


# =========================================================
# ZELVÉN INFORMATION
# =========================================================

BRAND_INFO = """
اسم العلامة: ZELVÉN

ZELVÉN هي علامة عطور فاخرة.
المتجر يقدم عطورًا مستوحاة من عطور عالمية.

الأسعار الحالية:
45 درهم للقنينة 30ML.

التوصيل:
داخل أكادير.

الدفع:
عند الاستلام.

رقم واتساب:
+212649982831

مهم:
- لا تخترع منتجات.
- لا تخترع أسعارًا.
- لا تخترع معلومات غير موجودة.
- إذا لم تكن متأكدًا من معلومة، قل للزبون أنك ستساعده في التحقق.
"""

# =========================================================
# PRODUCTS
# =========================================================

PRODUCTS = [
    {
        "id": "stronger-intensely",
        "name": "STRONGER WITH YOU INTENSELY",
        "type": "عطر مستوحى",
        "family": "شرقي",
        "notes": ["فانيليا", "عنبر", "لافندر"],
        "price": 45,
        "size": "30ML",
        "badge": "الأكثر مبيعاً",
    },
    {
        "id": "bleu-de-chanel",
        "name": "BLEU DE CHANEL",
        "type": "عطر مستوحى",
        "family": "خشبي",
        "notes": ["خشب الصندل", "حمضيات", "زنجبيل"],
        "price": 45,
        "size": "30ML",
        "badge": "",
    },
    {
        "id": "one-million",
        "name": "1 MILLION",
        "type": "عطر مستوحى",
        "family": "حار",
        "notes": ["جلد", "عنبر", "قرفة"],
        "price": 45,
        "size": "30ML",
        "badge": "إصدار مميز",
    },
    {
        "id": "ultra-male",
        "name": "ULTRA MALE",
        "type": "عطر مستوحى",
        "family": "شرقي",
        "notes": ["كمثرى", "فانيليا", "مسك"],
        "price": 45,
        "size": "30ML",
        "badge": "",
    },
    {
        "id": "imagination-lv",
        "name": "IMAGINATION LOUIS VUITTON",
        "type": "عطر مستوحى",
        "family": "منعش",
        "notes": ["شاي أسود", "حمضيات", "خشب الأرز"],
        "price": 45,
        "size": "30ML",
        "badge": "جديد",
    },
]


def products_text():
    result = []

    for product in PRODUCTS:
        result.append(
            f"""
المنتج: {product['name']}
النوع: {product['type']}
العائلة: {product['family']}
النوتات: {', '.join(product['notes'])}
الحجم: {product['size']}
السعر: {product['price']} درهم
"""
        )

    return "\n".join(result)


# =========================================================
# MEMORY
# =========================================================

# ملاحظة:
# SQLite على Vercel ليست ذاكرة دائمة.
# نستخدم /tmp حتى لا نحاول الكتابة إلى filesystem دائم.
DB_FILE = "/tmp/zelven_memory.db"


def get_db():
    return sqlite3.connect(
        DB_FILE,
        timeout=10
    )


def init_db():
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS processed_events (
                event_id TEXT PRIMARY KEY,
                created_at REAL NOT NULL
            )
            """
        )

        conn.commit()
        conn.close()

    except Exception as e:
        print(
            "Database initialization error:",
            repr(e)
        )


init_db()


def save_message(user_id, role, message):
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO messages
            (user_id, role, message, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                role,
                message,
                time.time()
            ),
        )

        conn.commit()
        conn.close()

    except Exception as e:
        print(
            "Memory save error:",
            repr(e)
        )


def get_history(user_id, limit=10):
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT role, message
            FROM messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                user_id,
                limit
            ),
        )

        rows = cursor.fetchall()

        conn.close()

        rows.reverse()

        return rows

    except Exception as e:
        print(
            "Memory read error:",
            repr(e)
        )

        return []


def event_already_processed(event_id):
    if not event_id:
        return False

    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT event_id
            FROM processed_events
            WHERE event_id = ?
            """,
            (event_id,),
        )

        exists = cursor.fetchone() is not None

        conn.close()

        return exists

    except Exception as e:
        print(
            "Event check error:",
            repr(e)
        )

        return False


def mark_event_processed(event_id):
    if not event_id:
        return

    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR IGNORE INTO processed_events
            (event_id, created_at)
            VALUES (?, ?)
            """,
            (
                event_id,
                time.time()
            ),
        )

        conn.commit()
        conn.close()

    except Exception as e:
        print(
            "Event save error:",
            repr(e)
        )


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def normalize_text(text):
    if not text:
        return ""

    text = text.lower().strip()

    replacements = {
        "salam 3likom": "سلام عليكم",
        "salam 3alaykom": "سلام عليكم",
        "slm 3likom": "سلام عليكم",
        "salam": "سلام",
        "slm": "سلام",

        "labas": "لاباس",
        "la bas": "لاباس",

        "kidayr": "كيف داير",
        "kidayra": "كيف دايرة",
        "kif dayr": "كيف داير",

        "bghit": "بغيت",
        "baghi": "باغي",
        "bghina": "بغينا",

        "parfum": "عطر",
        "parfume": "عطر",
        "parfums": "عطور",

        "ch7al": "شحال",
        "chhal": "شحال",

        "prix": "الثمن",
        "price": "الثمن",

        "commande": "طلب",
        "order": "طلب",

        "livraison": "التوصيل",
        "delivery": "التوصيل",

        "homme": "رجالي",
        "rajl": "رجالي",
        "lrajl": "رجالي",

        "femme": "نسائي",
        "mra": "نسائي",

        "merci": "شكرا",
        "thank you": "شكرا",
    }

    for old, new in sorted(
        replacements.items(),
        key=lambda item: len(item[0]),
        reverse=True
    ):
        text = text.replace(
            old,
            new
        )

    return text


# =========================================================
# INTENT
# =========================================================

def detect_intent(text):
    t = normalize_text(text)

    if any(x in t for x in [
        "سلام",
        "لاباس",
        "كيف داير",
        "مرحبا",
        "اهلا",
    ]):
        return "greeting"

    if any(x in t for x in [
        "الثمن",
        "شحال",
        "السعر",
        "درهم",
        "prix",
    ]):
        return "price"

    if any(x in t for x in [
        "التوصيل",
        "delivery",
        "livraison",
        "يوصل",
        "توصلي",
    ]):
        return "delivery"

    if any(x in t for x in [
        "بغيت",
        "باغي",
        "طلب",
        "commande",
        "نطلب",
        "نشري",
        "شراء",
    ]):
        return "order"

    if any(x in t for x in [
        "عطور",
        "عطر",
        "parfum",
        "parfums",
    ]):
        return "products"

    return "general"


# =========================================================
# GEMINI SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = f"""
أنت ZELVÉN AI، المساعد الرسمي لعلامة ZELVÉN للعطور.

مهمتك:
مساعدة زبائن ZELVÉN على Instagram بطريقة طبيعية وذكية.

{BRAND_INFO}

كتالوج المنتجات:
{products_text()}

===============================
أسلوب الكلام
===============================

تحدث بطريقة مغربية طبيعية.

يمكنك استعمال:
- العربية
- الدارجة المغربية
- الدارجة بالحروف اللاتينية
- الفرنسية
- خليط بينها عندما يتحدث الزبون بهذه الطريقة.

إذا كتب الزبون بالدارجة، رد بالدارجة.

إذا كتب بالفرنسية، رد بالفرنسية.

إذا خلط اللغات، يمكنك الرد بنفس الأسلوب.

===============================
قواعد مهمة
===============================

1. لا تقل "مرحبًا بك في ZELVÉN" في كل رسالة.
2. لا تكرر نفس الرد.
3. افهم الأخطاء الإملائية.
4. افهم الدارجة باللاتينية.
5. "slm" تعني السلام.
6. "ch7al" تعني شحال / السعر.
7. "bghit parfum" تعني أريد عطرًا.
8. "lrajl" تعني رجالي.
9. لا تخترع منتجات.
10. لا تخترع أسعارًا.
11. السعر هو 45 درهم لـ 30ML.
12. التوصيل حاليًا داخل أكادير.
13. الدفع عند الاستلام.
14. إذا أراد الزبون الشراء، ساعده في إتمام الطلب.
15. لا تطلب معلومات شخصية بلا سبب.
16. إذا كان السؤال غير واضح، اسأل سؤالًا قصيرًا.
17. لا تقل إنك Gemini.
18. لا تقل إنك روبوت.
19. أنت تمثل ZELVÉN.
20. اجعل الرد مناسبًا لـ Instagram.
21. استعمل الإيموجي باعتدال.

===============================
الطلبات
===============================

إذا أراد الزبون طلب منتج:

ساعده أولًا في تحديد:
- العطر
- الكمية

ثم يمكن طلب:
- الاسم
- المدينة
- العنوان
- رقم الهاتف

لا تطلب كل المعلومات دفعة واحدة إذا لم تكن ضرورية.

أجب فقط على آخر رسالة للزبون.
"""


# =========================================================
# AI RESPONSE
# =========================================================

def generate_ai_reply(user_id, user_message):

    if not gemini:

        return (
            "سمح ليا 🌸 كاين مشكل مؤقت فالمساعد الذكي. "
            "تقدر تتواصل معنا عبر واتساب."
        )

    history = get_history(
        user_id,
        limit=10
    )

    conversation = []

    for role, message in history:

        conversation.append(
            f"{role.upper()}: {message}"
        )

    normalized = normalize_text(
        user_message
    )

    intent = detect_intent(
        user_message
    )

    prompt = f"""
{SYSTEM_PROMPT}

===============================
نوع الرسالة
===============================

{intent}

===============================
المحادثة السابقة
===============================

{chr(10).join(conversation)}

===============================
رسالة الزبون الحالية
===============================

{user_message}

===============================
فهم الدارجة
===============================

{normalized}

اكتب الرد المناسب فقط.
لا تشرح طريقة عملك.
"""

    try:

        response = gemini.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )

        reply = (
            response.text or ""
        ).strip()

        if not reply:

            return (
                "سمح ليا 🌸 ما فهمتش الرسالة مزيان. "
                "عاود كتبها ليا."
            )

        if len(reply) > 1000:

            reply = (
                reply[:1000]
                .rsplit(" ", 1)[0]
                + "..."
            )

        return reply

    except Exception as e:

        print(
            "Gemini error:",
            repr(e)
        )

        return (
            "سمح ليا 🌸 وقع مشكل مؤقت. "
            "عاود صيفط ليا الرسالة."
        )


# =========================================================
# META SIGNATURE
# =========================================================

def verify_signature(raw_body):

    if not META_APP_SECRET:

        return True

    signature = request.headers.get(
        "X-Hub-Signature-256",
        ""
    )

    if not signature.startswith(
        "sha256="
    ):

        return False

    received = signature.replace(
        "sha256=",
        "",
        1
    )

    expected = hmac.new(
        META_APP_SECRET.encode(
            "utf-8"
        ),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(
        received,
        expected
    )


# =========================================================
# SEND INSTAGRAM MESSAGE
# =========================================================

def send_instagram_message(
    recipient_id,
    message
):

    if not INSTAGRAM_ACCESS_TOKEN:

        print(
            "ERROR: INSTAGRAM_ACCESS_TOKEN missing"
        )

        return False

    url = (
        "https://graph.instagram.com/"
        "v26.0/me/messages"
    )

    payload = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message
        },
        "access_token": (
            INSTAGRAM_ACCESS_TOKEN
        ),
    }

    try:

        response = requests.post(
            url,
            json=payload,
            timeout=20
        )

        print(
            "Instagram status:",
            response.status_code
        )

        print(
            "Instagram response:",
            response.text
        )

        return response.ok

    except Exception as e:

        print(
            "Instagram send error:",
            repr(e)
        )

        return False


# =========================================================
# PROCESS MESSAGE
# =========================================================

def process_message(
    sender_id,
    message_text,
    event_id
):

    try:

        if event_id:

            mark_event_processed(
                event_id
            )

        print(
            "Incoming message:",
            sender_id,
            message_text
        )

        save_message(
            sender_id,
            "user",
            message_text
        )

        reply = generate_ai_reply(
            sender_id,
            message_text
        )

        print(
            "ZELVÉN AI:",
            reply
        )

        save_message(
            sender_id,
            "assistant",
            reply
        )

        success = send_instagram_message(
            sender_id,
            reply
        )

        if not success:

            print(
                "ERROR: message not sent"
            )

    except Exception as e:

        print(
            "Background processing error:",
            repr(e)
        )


# =========================================================
# WEBHOOK VERIFICATION
# =========================================================

@app.route(
    "/",
    # Vercel
application = app
    methods=["GET"]
)
def verify_webhook():

    mode = request.args.get(
        "hub.mode"
    )

    token = request.args.get(
        "hub.verify_token"
    )

    challenge = request.args.get(
        "hub.challenge"
    )

    print(
        "Webhook verification:",
        mode,
        token
    )

    if (
        mode == "subscribe"
        and token == VERIFY_TOKEN
    ):

        return (
            challenge or "OK",
            200
        )

    return (
        "Forbidden",
        403
    )


# =========================================================
# INSTAGRAM WEBHOOK
# =========================================================

@app.route(
    "/",
    methods=["POST"]
)
def instagram_webhook():

    raw_body = request.get_data()

    if not verify_signature(
        raw_body
    ):

        print(
            "Invalid Meta signature"
        )

        return (
            "Forbidden",
            403
        )

    try:

        body = request.get_json(
            silent=True
        ) or {}

        print(
            "Instagram webhook:",
            json.dumps(
                body,
                ensure_ascii=False
            )
        )

        for entry in body.get(
            "entry",
            []
        ):

            for event in entry.get(
                "messaging",
                []
            ):

                sender = event.get(
                    "sender",
                    {}
                )

                sender_id = sender.get(
                    "id"
                )

                message = event.get(
                    "message",
                    {}
                )

                message_text = message.get(
                    "text"
                )

                event_id = (
                    message.get("mid")
                    or event.get("id")
                )

                if (
                    not sender_id
                    or not message_text
                ):

                    continue

                if message.get(
                    "is_echo"
                ):

                    continue

                if event_already_processed(
                    event_id
                ):

                    print(
                        "Duplicate event:",
                        event_id
                    )

                    continue

                thread = threading.Thread(
                    target=process_message,
                    args=(
                        sender_id,
                        message_text,
                        event_id
                    ),
                    daemon=True
                )

                thread.start()

        return (
            "EVENT_RECEIVED",
            200
        )

    except Exception as e:

        print(
            "Webhook error:",
            repr(e)
        )

        return (
            "EVENT_RECEIVED",
            200
        )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route(
    "/health",
    methods=["GET"]
)
def health():

    return jsonify(
        {
            "status": "ok",
            "brand": "ZELVÉN",
            "ai": bool(
                GEMINI_API_KEY
            ),
            "instagram": bool(
                INSTAGRAM_ACCESS_TOKEN
            ),
            "verify_token": bool(
                VERIFY_TOKEN
            ),
            "products": len(
                PRODUCTS
            )
        }
    )


# =========================================================
# VERCEL ENTRYPOINT
# =========================================================

# هذا المتغير موجود بشكل صريح
# ليساعد Vercel على اكتشاف Flask application.
application = app


# =========================================================
# LOCAL DEVELOPMENT ONLY
# =========================================================

if __name__ == "__main__":

    port = int(
        os.getenv(
            "PORT",
            "5000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
