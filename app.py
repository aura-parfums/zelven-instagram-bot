import os
import re
import requests
from flask import Flask, request

app = Flask(__name__)

# =========================================================
# ZELVÉN BOT-IG
# =========================================================

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")

# يدعم الاسمين حتى لا تحتاج إلى تغيير المتغير الموجود عندك
ACCESS_TOKEN = (
    os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    or os.environ.get("ACCESS_TOKEN")
)

INSTAGRAM_USER_ID = os.environ.get("INSTAGRAM_USER_ID")
APP_SECRET = os.environ.get("APP_SECRET")

GRAPH_VERSION = "v26.0"


# =========================================================
# ZELVÉN INFORMATION
# =========================================================

BRAND_NAME = "ZELVÉN"

CITY = "أكادير"

WHATSAPP_NUMBER = "212649982831"

DELIVERY_INFO = (
    "نوفر التوصيل داخل مدينة أكادير 🚚✨\n"
    "والدفع عند الاستلام."
)


# =========================================================
# PRODUCTS
# =========================================================

PRODUCTS = [
    {
        "id": "stronger-intensely",
        "name": "STRONGER WITH YOU INTENSELY",
        "arabic": "سترونغر وذ يو إنتنسلي",
        "family": "شرقي",
        "notes": ["فانيليا", "عنبر", "لافندر"],
        "price": 45,
        "size": "30ML",
        "badge": "الأكثر مبيعاً",
    },
    {
        "id": "bleu-de-chanel",
        "name": "BLEU DE CHANEL",
        "arabic": "بلو دو شانيل",
        "family": "خشبي",
        "notes": ["خشب الصندل", "حمضيات", "زنجبيل"],
        "price": 45,
        "size": "30ML",
        "badge": "",
    },
    {
        "id": "one-million",
        "name": "1 MILLION",
        "arabic": "وان مليون",
        "family": "حار",
        "notes": ["جلد", "عنبر", "قرفة"],
        "price": 45,
        "size": "30ML",
        "badge": "إصدار مميز",
    },
    {
        "id": "ultra-male",
        "name": "ULTRA MALE",
        "arabic": "ألترا ميل",
        "family": "شرقي",
        "notes": ["كمثرى", "فانيليا", "مسك"],
        "price": 45,
        "size": "30ML",
        "badge": "",
    },
    {
        "id": "imagination-lv",
        "name": "IMAGINATION LOUIS VUITTON",
        "arabic": "إماجينيشن لويس فويتون",
        "family": "منعش",
        "notes": ["شاي أسود", "حمضيات", "خشب الأرز"],
        "price": 45,
        "size": "30ML",
        "badge": "جديد",
    },
]


# =========================================================
# HELPERS
# =========================================================

def normalize(text):
    if not text:
        return ""

    text = text.lower().strip()

    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ة": "ه",
        "ى": "ي",
        "ؤ": "و",
        "ئ": "ي",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return re.sub(r"\s+", " ", text)


def product_list_text():
    lines = [
        "هذه هي تشكيلة ZELVÉN الحالية ✨",
        ""
    ]

    for p in PRODUCTS:
        badge = f" — {p['badge']}" if p["badge"] else ""

        lines.append(
            f"🌟 {p['name']}{badge}\n"
            f"   {p['family']} | {p['size']} | {p['price']} درهم\n"
            f"   النوتات: {' • '.join(p['notes'])}"
        )

    lines.append("")
    lines.append("إذا أخبرتني بنوع العطر الذي تحبه، سأرشح لك الأنسب 🌸")

    return "\n".join(lines)


def product_details(product):
    return (
        f"✨ {product['name']}\n\n"
        f"🌿 العائلة: {product['family']}\n"
        f"🧴 الحجم: {product['size']}\n"
        f"💰 السعر: {product['price']} درهم\n"
        f"🌸 النوتات: {' • '.join(product['notes'])}\n"
        f"{'🏆 ' + product['badge'] if product['badge'] else ''}\n\n"
        f"إذا أردت طلبه، اكتب: «أريد طلب {product['name']}» 🛍️"
    )


# =========================================================
# PRODUCT SEARCH
# =========================================================

def find_product(text):
    t = normalize(text)

    aliases = {
        "stronger": "stronger-intensely",
        "stronger with you": "stronger-intensely",
        "intensely": "stronger-intensely",
        "سترونغر": "stronger-intensely",
        "سترونجر": "stronger-intensely",

        "bleu": "bleu-de-chanel",
        "bleu de chanel": "bleu-de-chanel",
        "بلو": "bleu-de-chanel",
        "شانيل": "bleu-de-chanel",

        "1 million": "one-million",
        "one million": "one-million",
        "وان مليون": "one-million",
        "مليون": "one-million",

        "ultra male": "ultra-male",
        "ultra": "ultra-male",
        "الترا": "ultra-male",
        "ألترا": "ultra-male",

        "imagination": "imagination-lv",
        "imagination louis vuitton": "imagination-lv",
        "imagination lv": "imagination-lv",
        "ايماجينيشن": "imagination-lv",
        "إماجينيشن": "imagination-lv",
    }

    for alias, product_id in aliases.items():
        if normalize(alias) in t:
            return next(
                (p for p in PRODUCTS if p["id"] == product_id),
                None
            )

    for product in PRODUCTS:
        if normalize(product["name"]) in t:
            return product

        if normalize(product["arabic"]) in t:
            return product

    return None


# =========================================================
# SMART RECOMMENDATIONS
# =========================================================

def recommend_product(text):
    t = normalize(text)

    # منعش
    if any(word in t for word in [
        "منعش",
        "فريش",
        "fresh",
        "خفيف",
        "صيف",
        "صيفي",
        "حمضيات",
        "citrus",
    ]):
        return next(
            p for p in PRODUCTS
            if p["id"] == "imagination-lv"
        )

    # خشبي
    if any(word in t for word in [
        "خشبي",
        "خشب",
        "wood",
        "woody",
        "رجولي",
        "راقي",
        "كلاسيكي",
    ]):
        return next(
            p for p in PRODUCTS
            if p["id"] == "bleu-de-chanel"
        )

    # شرقي
    if any(word in t for word in [
        "شرقي",
        "حلو",
        "حلوه",
        "فانيلا",
        "عنبر",
        "vanilla",
        "oriental",
    ]):
        return next(
            p for p in PRODUCTS
            if p["id"] == "stronger-intensely"
        )

    # حار
    if any(word in t for word in [
        "حار",
        "قوي",
        "spicy",
        "قرفة",
        "جلد",
    ]):
        return next(
            p for p in PRODUCTS
            if p["id"] == "one-million"
        )

    # مسك / حلو
    if any(word in t for word in [
        "مسك",
        "كمثرى",
        "ناعم",
    ]):
        return next(
            p for p in PRODUCTS
            if p["id"] == "ultra-male"
        )

    return None


# =========================================================
# INTELLIGENT REPLY ENGINE
# =========================================================

def create_reply(text):

    original = text or ""
    t = normalize(original)

    # -----------------------------------------------------
    # GREETING
    # -----------------------------------------------------

    if any(word in t for word in [
        "سلام",
        "السلام عليكم",
        "مرحبا",
        "اهلا",
        "هلا",
        "hello",
        "hi",
        "salam",
    ]):

        return (
            "وعليكم السلام ورحمة الله 🌸\n\n"
            "مرحبًا بك في **ZELVÉN** ✨\n"
            "يسعدني مساعدتك في اختيار العطر المناسب لك.\n\n"
            "لدينا عطور بحجم 30ML ابتداءً من **45 درهم**.\n\n"
            "يمكنني مساعدتك في:\n"
            "🌹 اختيار العطر المناسب\n"
            "💰 معرفة الأسعار\n"
            "🌿 معرفة النوتات\n"
            "🚚 معرفة التوصيل\n"
            "🛍️ تجهيز طلبك\n\n"
            "قل لي مثلاً:\n"
            "«بغيت عطر منعش»\n"
            "أو «شنو عندكم؟»"
        )

    # -----------------------------------------------------
    # PRODUCT LIST
    # -----------------------------------------------------

    if any(word in t for word in [
        "شنو عندكم",
        "ماذا عندكم",
        "العطور",
        "المنتجات",
        "لائحة",
        "catalogue",
        "collection",
        "عندكم",
    ]):

        return product_list_text()

    # -----------------------------------------------------
    # PRICE
    # -----------------------------------------------------

    product = find_product(original)

    if product and any(word in t for word in [
        "سعر",
        "ثمن",
        "كم",
        "بكم",
        "prix",
        "price",
    ]):

        return product_details(product)

    if any(word in t for word in [
        "سعر",
        "ثمن",
        "الاثمان",
        "الاسعار",
        "بكم",
        "prix",
        "price",
    ]):

        return (
            "جميع العطور المعروضة حاليًا بحجم **30ML** ✨\n\n"
            "💰 السعر: **45 درهم للقنينة**.\n\n"
            "إذا أردت، اكتب اسم العطر وسأعطيك تفاصيله كاملة."
        )

    # -----------------------------------------------------
    # DELIVERY
    # -----------------------------------------------------

    if any(word in t for word in [
        "توصيل",
        "التوصيل",
        "livraison",
        "delivery",
        "يوصل",
        "كتوصلو",
    ]):

        return (
            "نعم طبعًا 🚚✨\n\n"
            "📍 التوصيل متوفر داخل **أكادير**.\n"
            "💵 الدفع عند الاستلام.\n\n"
            "إذا أردت الطلب، أرسل لي اسم العطر والكمية وسأساعدك في إكمال الطلب."
        )

    # -----------------------------------------------------
    # CITY
    # -----------------------------------------------------

    if "اكادير" in t or "agadir" in t:

        return (
            "أكيد 🌸\n"
            "ZELVÉN يوفر التوصيل داخل **أكادير** 🚚\n"
            "والدفع عند الاستلام 💵."
        )

    # -----------------------------------------------------
    # RECOMMENDATION
    # -----------------------------------------------------

    recommendation = recommend_product(original)

    if recommendation:

        return (
            f"إذا كنت تبحث عن هذا النوع، أرشح لك شخصيًا:\n\n"
            f"✨ **{recommendation['name']}**\n\n"
            f"🌿 العائلة: {recommendation['family']}\n"
            f"🌸 النوتات: {' • '.join(recommendation['notes'])}\n"
            f"🧴 الحجم: {recommendation['size']}\n"
            f"💰 السعر: {recommendation['price']} درهم\n\n"
            f"{'🏆 ' + recommendation['badge'] if recommendation['badge'] else ''}\n\n"
            f"إذا أعجبك، قل لي: «أريد {recommendation['name']}» 🛍️"
        )

    # -----------------------------------------------------
    # ORDER INTENT
    # -----------------------------------------------------

    if any(word in t for word in [
        "بغيت نطلب",
        "اريد طلب",
        "ابغي نطلب",
        "بغيت ناخد",
        "غادي ناخد",
        "اريد شراء",
        "شراء",
        "order",
        "commander",
    ]):

        if product:
            return (
                f"بكل سرور 🌸\n\n"
                f"🛍️ اخترت: **{product['name']}**\n"
                f"💰 السعر: {product['price']} درهم\n"
                f"🧴 الحجم: {product['size']}\n\n"
                "لإكمال الطلب أرسل لي:\n"
                "👤 الاسم الكامل\n"
                "📍 الحي / العنوان في أكادير\n"
                "📞 رقم الهاتف\n"
                "🔢 الكمية"
            )

        return (
            "بكل سرور 🛍️✨\n\n"
            "أرسل لي أولًا اسم العطر الذي تريد طلبه.\n\n"
            "مثال:\n"
            "«بغيت نطلب BLEU DE CHANEL»"
        )

    # -----------------------------------------------------
    # NOTES
    # -----------------------------------------------------

    if product and any(word in t for word in [
        "نوت",
        "رائحة",
        "مكونات",
        "notes",
        "ريحة",
    ]):

        return (
            f"🌸 نوتات **{product['name']}**:\n\n"
            + "\n".join(
                f"• {note}"
                for note in product["notes"]
            )
            + f"\n\n💰 السعر: {product['price']} درهم"
        )

    # -----------------------------------------------------
    # THANK YOU
    # -----------------------------------------------------

    if any(word in t for word in [
        "شكرا",
        "شكراً",
        "merci",
        "thanks",
    ]):

        return (
            "العفو 🌸✨\n"
            "ZELVÉN دائمًا في خدمتك.\n\n"
            "إذا احتجت مساعدة في اختيار عطرك، أنا هنا 🤍"
        )

    # -----------------------------------------------------
    # HELP
    # -----------------------------------------------------

    if any(word in t for word in [
        "مساعدة",
        "ساعدني",
        "help",
        "شنو نقدر",
        "ماذا يمكن",
    ]):

        return (
            "أكيد 🌸\n\n"
            "يمكنني مساعدتك في:\n"
            "🌹 اختيار عطر مناسب\n"
            "💰 الأسعار\n"
            "🌿 النوتات العطرية\n"
            "🚚 التوصيل بأكادير\n"
            "🛍️ الطلب\n\n"
            "مثلاً اكتب:\n"
            "«بغيت عطر منعش»\n"
            "أو «شنو العطور عندكم؟»"
        )

    # -----------------------------------------------------
    # FALLBACK
    # -----------------------------------------------------

    return (
        "أهلاً بك في **ZELVÉN** 🌸✨\n\n"
        "فهمت رسالتك، ويمكنني مساعدتك في اختيار العطر المناسب.\n\n"
        "جرب أن تسألني مثلاً:\n"
        "🌿 «بغيت عطر منعش»\n"
        "🔥 «بغيت عطر قوي»\n"
        "🌲 «بغيت عطر خشبي»\n"
        "💰 «شنو الأسعار؟»\n"
        "🛍️ «بغيت نطلب BLEU DE CHANEL»\n"
        "🚚 «واش كاين التوصيل؟»"
    )


# =========================================================
# WEBHOOK VERIFICATION
# =========================================================

@app.route("/", methods=["GET"])
@app.route("/webhook", methods=["GET"])
def verify_webhook():

    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    print("Webhook verification request")
    print("Mode:", mode)
    print("Token received:", token)
    print("Secret exists:", bool(VERIFY_TOKEN))

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("Webhook verification successful")
        return challenge, 200

    return "Verification failed", 403


# =========================================================
# RECEIVE INSTAGRAM WEBHOOK
# =========================================================

@app.route("/", methods=["POST"])
@app.route("/webhook", methods=["POST"])
def receive_message():

    data = request.get_json(silent=True)

    print("Instagram webhook received")
    print("Data:", data)

    if not data:
        return "OK", 200

    try:

        for entry in data.get("entry", []):

            # Instagram Messaging API
            for messaging in entry.get("messaging", []):

                sender = messaging.get("sender", {})
                sender_id = sender.get("id")

                message = messaging.get("message", {})
                text = message.get("text")

                if not sender_id or not text:
                    continue

                print(
                    f"Message from {sender_id}: {text}"
                )

                reply = create_reply(text)

                print("BOT REPLY:", reply)

                send_message(
                    sender_id,
                    reply
                )

    except Exception as e:

        print(
            "Webhook processing error:",
            repr(e)
        )

    return "OK", 200


# =========================================================
# SEND MESSAGE TO INSTAGRAM
# =========================================================

def send_message(recipient_id, text):

    if not ACCESS_TOKEN:

        print(
            "ERROR: INSTAGRAM_ACCESS_TOKEN / ACCESS_TOKEN "
            "is missing."
        )

        return

    url = (
        f"https://graph.instagram.com/"
        f"{GRAPH_VERSION}/me/messages"
    )

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": text
        }
    }

    try:

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=20,
        )

        print(
            "Instagram API status:",
            response.status_code
        )

        print(
            "Instagram API response:",
            response.text
        )

    except Exception as e:

        print(
            "Instagram API error:",
            repr(e)
        )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health", methods=["GET"])
def health():

    return {
        "status": "ok",
        "bot": "ZELVÉN BOT-IG",
        "products": len(PRODUCTS),
        "access_token": bool(ACCESS_TOKEN),
        "verify_token": bool(VERIFY_TOKEN),
    }, 200


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
