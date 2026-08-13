```python
import os
import re
import json
import time
import hmac
import hashlib
import sqlite3
import threading
from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv
from google import genai

# =========================================================
# ZELVÉN AI BOT
# Instagram + Gemini + Memory + Products + Orders
# =========================================================

load_dotenv()

app = Flask(__name__)

# ---------------------------------------------------------
# ENVIRONMENT VARIABLES
# ---------------------------------------------------------

INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "").strip()
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "zelven_verify_2026").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
META_APP_SECRET = os.getenv("META_APP_SECRET", "").strip()

# يمكن تغييره من Environment Variables
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# رقم واتساب ZELVÉN
WHATSAPP_NUMBER = os.getenv("WHATSAPP_NUMBER", "212649982831")

# ---------------------------------------------------------
# GEMINI
# ---------------------------------------------------------

if GEMINI_API_KEY:
    gemini = genai.Client(api_key=GEMINI_API_KEY)
else:
    gemini = None


# =========================================================
# ZELVÉN KNOWLEDGE BASE
# =========================================================

BRAND_INFO = """
اسم العلامة: ZELVÉN

ZELVÉN هي علامة عطور فاخرة.
المتجر يقدم عطورًا مستوحاة من عطور عالمية.
الأسعار الموجودة حاليًا في الكتالوج هي 45 درهم للقنينة 30ML.
التوصيل حاليًا في أكادير.
الدفع عند الاستلام.
رقم واتساب: +212649982831

مهم:
- لا تخترع منتجات غير موجودة.
- لا تخترع أسعارًا.
- لا تقل إن المنتج متوفر إذا لم يكن موجودًا في الكتالوج.
- إذا لم تكن متأكدًا من معلومة، قل للزبون أنك ستساعده في التحقق.
"""

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

    for p in PRODUCTS:
        result.append(
            f"""
المنتج: {p['name']}
النوع: {p['type']}
العائلة: {p['family']}
النوتات: {', '.join(p['notes'])}
الحجم: {p['size']}
السعر: {p['price']} درهم
"""
        )

    return "\n".join(result)


# =========================================================
# DATABASE / MEMORY
# =========================================================

DB_FILE = "zelven_memory.db"


def init_db():
    conn = sqlite3.connect(DB_FILE)
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


init_db()


def save_message(user_id, role, message):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO messages
            (user_id, role, message, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, role, message, time.time()),
        )

        conn.commit()
        conn.close()

    except Exception as e:
        print("Memory save error:", e)


def get_history(user_id, limit=12):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT role, message
            FROM messages
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        )

        rows = cursor.fetchall()
        conn.close()

        rows.reverse()
        return rows

    except Exception as e:
        print("Memory read error:", e)
        return []


def event_already_processed(event_id):
    if not event_id:
        return False

    try:
        conn = sqlite3.connect(DB_FILE)
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
        print("Event check error:", e)
        return False


def mark_event_processed(event_id):
    if not event_id:
        return

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR IGNORE INTO processed_events
            (event_id, created_at)
            VALUES (?, ?)
            """,
            (event_id, time.time()),
        )

        conn.commit()
        conn.close()

    except Exception as e:
        print("Event save error:", e)


# =========================================================
# NORMALIZE DARIJA / LATIN
# =========================================================

def normalize_text(text):
    if not text:
        return ""

    text = text.lower().strip()

    replacements = {
        "salam": "سلام",
        "slm": "سلام",
        "salam 3likom": "سلام عليكم",
        "salam 3alaykom": "سلام عليكم",
        "slm 3likom": "سلام عليكم",

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

    # نبدأ بالأطول حتى لا يحدث استبدال خاطئ
    for old, new in sorted(
        replacements.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    ):
        text = text.replace(old, new)

    return text


# =========================================================
# QUICK INTENT
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
# GEMINI PROMPT
# =========================================================

SYSTEM_PROMPT = f"""
أنت ZELVÉN AI، المساعد الرسمي لعلامة ZELVÉN للعطور.

مهمتك:
مساعدة زبائن ZELVÉN على Instagram بطريقة طبيعية وذكية جدًا.

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
- الدارجة المكتوبة بالحروف اللاتينية
- الفرنسية
- خليط بينها عندما يتحدث الزبون بهذه الطريقة.

مثال:
الزبون: "slm kidayr labas"
الرد المناسب:
"وعليكم السلام 🌸 لاباس الحمد لله، مرحباً بك فـ ZELVÉN ✨ شنو نقدر نعاونك فيه؟"

الزبون:
"bghit parfum zwine lrajl"

يمكن أن تقول:
"أكيد ✨ إلا كنت باغي parfum رجالي، عندنا BLEU DE CHANEL و STRONGER WITH YOU INTENSELY و ULTRA MALE و 1 MILLION. إلا بغيتي نقدر نرشح ليك واحد حسب واش كتفضل parfum frais، sucré ولا قوي."

لا تكرر نفس الجملة في كل مرة.

===============================
قواعد مهمة
===============================

1. لا تقل "مرحبًا بك في ZELVÉN" في كل رسالة.
2. لا تجب بنفس النص إذا تغير سؤال الزبون.
3. افهم الأخطاء الإملائية.
4. افهم الدارجة باللاتينية.
5. إذا قال الزبون "slm" اعتبرها سلام.
6. إذا قال "ch7al" افهم أنه يسأل عن السعر.
7. إذا قال "bghit parfum" افهم أنه يريد عطرًا.
8. إذا قال "lrajl" افهم أنه يريد عطرًا رجاليًا.
9. لا تخترع عطورًا أو أسعارًا.
10. السعر الموجود في الكتالوج هو 45 درهم للقنينة 30ML.
11. التوصيل الموجود حاليًا هو أكادير.
12. الدفع عند الاستلام.
13. إذا أراد الزبون الشراء، ساعده في إتمام الطلب.
14. لا تطلب معلومات شخصية بلا سبب.
15. إذا كان السؤال غير واضح، اسأل سؤالًا قصيرًا بدل الرد الطويل.
16. لا تقل إنك Gemini.
17. لا تقل إنك روبوت.
18. أنت تمثل ZELVÉN.
19. حافظ على رد قصير ومناسب لـ Instagram.
20. استعمل الإيموجي باعتدال.
21. إذا كتب الزبون بالفرنسية، يمكنك الرد بالفرنسية.
22. إذا كتب بالدارجة، رد بالدارجة.
23. إذا خلط العربية والفرنسية، يمكنك الخلط بشكل طبيعي.

===============================
الطلبات
===============================

إذا كان الزبون يريد commande، ساعده في اختيار المنتج والكمية.

بعد التأكد من المنتج، يمكن طلب:
- الاسم
- المدينة
- العنوان
- رقم الهاتف

لكن لا تطلب كل شيء دفعة واحدة إذا لم يكن ذلك ضروريًا.

===============================
ذاكرة المحادثة
===============================

ستجد أسفل هذا النص جزءًا من المحادثة السابقة.
استعمله لفهم سياق الزبون وعدم إعادة الأسئلة التي أجاب عنها مسبقًا.

أجب فقط على آخر رسالة للزبون.
"""


# =========================================================
# GEMINI RESPONSE
# =========================================================

def generate_ai_reply(user_id, user_message):
    if not gemini:
        return (
            "سمح ليا 🌸 كاين مشكل مؤقت فالمساعد الذكي. "
            "تقدر تتواصل معنا مباشرة عبر واتساب."
        )

    history = get_history(user_id, limit=10)

    conversation = []

    for role, message in history:
        conversation.append(
            f"{role.upper()}: {message}"
        )

    normalized = normalize_text(user_message)
    intent = detect_intent(user_message)

    prompt = f"""
{SYSTEM_PROMPT}

===============================
نوع الرسالة المتوقع
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
نسخة مساعدة بعد فهم الدارجة
===============================

{normalized}

اكتب الآن الرد المناسب فقط.
لا تضف شرحًا عن طريقة عملك.
"""

    try:
        response = gemini.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )

        reply = (response.text or "").strip()

        if not reply:
            return "سمح ليا 🌸 ما قدرتش نفهم الرسالة مزيان. عاود كتبها ليا."

        # حماية بسيطة من الردود الطويلة جدًا
        if len(reply) > 1000:
            reply = reply[:1000].rsplit(" ", 1)[0] + "..."

        return reply

    except Exception as e:
        print("Gemini error:", repr(e))

        return (
            "سمح ليا 🌸 وقع مشكل مؤقت. "
            "عاود صيفط ليا الرسالة من فضلك."
        )


# =========================================================
# INSTAGRAM SIGNATURE VERIFICATION
# =========================================================

def verify_signature(raw_body):
    if not META_APP_SECRET:
        # إذا لم تضف App Secret نسمح مؤقتًا
        # لكن يفضل إضافته لاحقًا.
        return True

    signature = request.headers.get("X-Hub-Signature-256", "")

    if not signature.startswith("sha256="):
        return False

    received = signature.replace("sha256=", "", 1)

    expected = hmac.new(
        META_APP_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(received, expected)


# =========================================================
# SEND INSTAGRAM MESSAGE
# =========================================================

def send_instagram_message(recipient_id, message):
    if not INSTAGRAM_ACCESS_TOKEN:
        print("ERROR: INSTAGRAM_ACCESS_TOKEN is missing")
        return False

    url = "https://graph.instagram.com/v26.0/me/messages"

    payload = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message
        },
        "access_token": INSTAGRAM_ACCESS_TOKEN,
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=20,
        )

        print(
            "Instagram send status:",
            response.status_code
        )

        print(
            "Instagram send response:",
            response.text
        )

        if response.ok:
            return True

        return False

    except Exception as e:
        print(
            "Instagram send exception:",
            repr(e)
        )
        return False


# =========================================================
# PROCESS INSTAGRAM MESSAGE
# =========================================================

def process_message(sender_id, message_text, event_id):
    try:
        if event_id:
            mark_event_processed(event_id)

        print(
            f"Incoming Instagram message from {sender_id}: "
            f"{message_text}"
        )

        # حفظ رسالة المستخدم
        save_message(
            sender_id,
            "user",
            message_text,
        )

        # توليد الرد
        reply = generate_ai_reply(
            sender_id,
            message_text,
        )

        print(
            f"ZELVÉN AI reply: {reply}"
        )

        # حفظ الرد في الذاكرة
        save_message(
            sender_id,
            "assistant",
            reply,
        )

        # إرسال الرد
        success = send_instagram_message(
            sender_id,
            reply,
        )

        if not success:
            print(
                "ERROR: Instagram message was not sent."
            )

    except Exception as e:
        print(
            "Background processing error:",
            repr(e)
        )


# =========================================================
# WEBHOOK VERIFICATION
# =========================================================

@app.route("/", methods=["GET"])
def verify_webhook():

    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    print(
        "Webhook verification:",
        mode,
        token,
    )

    if (
        mode == "subscribe"
        and token == VERIFY_TOKEN
    ):
        return challenge or "OK", 200

    return "Forbidden", 403


# =========================================================
# WEBHOOK RECEIVE
# =========================================================

@app.route("/", methods=["POST"])
def instagram_webhook():

    raw_body = request.get_data()

    # التحقق من Meta signature
    if not verify_signature(raw_body):
        print("Invalid Meta signature")
        return "Forbidden", 403

    try:
        body = request.get_json(
            silent=True
        ) or {}

        print(
            "Instagram webhook received:",
            json.dumps(
                body,
                ensure_ascii=False
            )
        )

        # -------------------------------------------------
        # Instagram webhook
        # -------------------------------------------------

        for entry in body.get("entry", []):

            messaging_events = entry.get(
                "messaging",
                []
            )

            for event in messaging_events:

                sender = event.get(
                    "sender",
                    {}
                )

                sender_id = sender.get("id")

                message = event.get(
                    "message",
                    {}
                )

                message_text = message.get(
                    "text"
                )

                # Instagram message ID
                event_id = (
                    message.get("mid")
                    or event.get("id")
                )

                # تجاهل الأحداث التي ليست رسائل نصية
                if not sender_id or not message_text:
                    continue

                # تجاهل الرسائل التي أرسلها البوت نفسه
                if message.get("is_echo"):
                    continue

                # منع الرد مرتين على نفس الرسالة
                if event_already_processed(event_id):
                    print(
                        "Duplicate event ignored:",
                        event_id
                    )
                    continue

                # -------------------------------------------------
                # نرسل 200 بسرعة إلى Meta ثم نعالج الرسالة
                # -------------------------------------------------

                thread = threading.Thread(
                    target=process_message,
                    args=(
                        sender_id,
                        message_text,
                        event_id,
                    ),
                    daemon=True,
                )

                thread.start()

        return "EVENT_RECEIVED", 200

    except Exception as e:

        print(
            "Webhook error:",
            repr(e)
        )

        # Meta يجب أن تحصل على 200
        # حتى لا تعيد إرسال نفس الحدث باستمرار.
        return "EVENT_RECEIVED", 200


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health", methods=["GET"])
def health():

    return jsonify(
        {
            "status": "ok",
            "brand": "ZELVÉN",
            "ai": bool(GEMINI_API_KEY),
            "instagram": bool(INSTAGRAM_ACCESS_TOKEN),
        }
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    port = int(
        os.getenv("PORT", "5000")
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
    )
```
