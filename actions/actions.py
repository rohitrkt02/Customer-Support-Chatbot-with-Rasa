# =============================================================
#  actions/actions.py
#  Aroma & Co. — Café Chatbot with Gemini AI Fallback
#
#  HOW IT WORKS:
#  ┌─────────────────────────────────────────────────────┐
#  │  User sends message                                 │
#  │       ↓                                             │
#  │  Rasa NLU classifies intent                         │
#  │       ↓                                             │
#  │  Confidence >= 0.3?                                 │
#  │    YES → Rasa handles it (booking, slots, menu...)  │
#  │    NO  → FallbackClassifier triggers                │
#  │            → ActionGeminiFallback called            │
#  │            → Gemini AI answers with café context   │
#  └─────────────────────────────────────────────────────┘
#
#  Gemini is ALSO used inside:
#    • action_menu_info    → richer item descriptions
#    • action_cafe_info    → for unknown/complex questions
#    • action_gemini_chat  → free-form café conversation
# =============================================================

from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from rasa_sdk.events import SlotSet
import sqlite3
import logging
import random
import string
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── GEMINI SETUP ─────────────────────────────────────────────
# Step 1: pip install google-generativeai
# Step 2: Get free API key at https://aistudio.google.com/app/apikey
# Step 3: export GEMINI_API_KEY="your_key_here"
#         OR replace the empty string below directly

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Full café context injected into every Gemini prompt
CAFE_SYSTEM_CONTEXT = """
You are the friendly virtual assistant for Aroma & Co., an artisan café.

CAFÉ DETAILS:
- Name    : Aroma & Co.
- Address : 12-A Hazratganj, Lucknow – 226 001
- Phone   : +91 8303920943
- Email   : rohit@aromaandco.in
- Hours   : Mon–Fri 8AM–10PM | Sat–Sun 8AM–11PM
- WiFi    : Network: AromaCo_Guests | Password: coffeeislife
- Payment : Cards, UPI, cash accepted
- Parking : Hazratganj Parking Complex (2-min walk)

EVENTS:
- Live Jazz Night : Every Fri & Sat, 7–10 PM
- Barista Workshop: Every Sunday, 10 AM (₹799/person)
- Private Events  : Up to 30 guests (birthdays, off-sites)

DIETARY:
- Vegan items available | Gluten-free on request
- Oat milk, almond milk, soy milk available

FULL MENU:
☕ COFFEE
  Espresso Classico ₹120 — Pure bold 25ml shot, Ethiopian blend
  Signature Latte ₹220 — Velvety microfoam, double ristretto. Bestseller!
  Cold Brew Reserve ₹280 — 18-hour slow-steeped Colombian over large ice
  Honey Cardamom Flat White ₹260 — Spiced, golden and comforting
  Matcha Cortado ₹290 — Ceremonial matcha meets espresso
  Dark Mocha ₹250 — 72% Valrhona cocoa with house espresso

🥐 FOOD
  Butter Croissant ₹160 — French-style, laminated 27 times
  Truffle Mushroom Toast ₹380 — Sourdough, ricotta, mushrooms, black truffle oil
  Seasonal Grain Bowl ₹350 — Farro, veggies, tahini. Vegan
  Eggs Benedict ₹420 — Poached eggs, hollandaise, smoked salmon on brioche
  Brown Butter Banana Cake ₹290 — Warm slice with vanilla bean gelato
  Cheese & Charcuterie Board ₹680 — Seasonal selection, house preserves, crackers

🌸 SPECIALS
  Rose Saffron Latte ₹320 — Saffron milk, rose water, pistachio. Lucknow special!
  Espresso Tonic ₹300 — Double shot over tonic, lemon peel. Effervescent
  Masala Spice Brew ₹220 — Single origin with fresh desi spice blend
  Blueberry Lavender Latte ₹310 — Blueberry, lavender syrup, oat milk over ice
  Hojicha Latte ₹280 — Roasted Japanese green tea. Perfect for evenings
  Celebration Brunch Set ₹1200 — Curated spread for two

🍹 DRINKS
  Sparkling Lemonade ₹180 | Summer Berry Cooler ₹220
  Alphonso Mango Lassi ₹200 | Single Estate Darjeeling ₹160
  Fresh Pressed Juice ₹160 | House Kombucha ₹240

RESPONSE STYLE:
- Be warm, friendly, and conversational — like a knowledgeable café host
- Keep responses concise (2-4 sentences unless listing items)
- Use emojis naturally but sparingly
- Always respond in the same language as the user
- Never make up prices or items not listed above
- If asked to book a table, collect: name, date, time, guest count
"""


def get_gemini_response(user_message: str, extra_context: str = "") -> str:
    """
    Send a message to Gemini 1.5 Flash (free tier) and return the response.
    Returns None if Gemini is unavailable so caller can use Rasa fallback.
    """
    if not GEMINI_API_KEY or GEMINI_API_KEY == "":
        logger.warning("GEMINI_API_KEY not set. Skipping Gemini call.")
        return None

    try:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)

        # gemini-1.5-flash is free tier, fast, and high quality
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=CAFE_SYSTEM_CONTEXT + extra_context
        )

        response = model.generate_content(user_message)
        return response.text.strip()

    except ImportError:
        logger.error("google-generativeai not installed. Run: pip install google-generativeai")
        return None
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
#  SECTION 1 — TABLE RESERVATION
# ═══════════════════════════════════════════════════════════════

class ActionReserveTable(Action):
    def name(self) -> Text:
        return "action_reserve_table"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        name   = tracker.get_slot("customer_name")
        date   = tracker.get_slot("booking_date")
        time   = tracker.get_slot("booking_time")
        guests = tracker.get_slot("guest_count")

        if not all([name, date, time, guests]):
            dispatcher.utter_message(
                text="I still need your name, preferred date, time, and number of guests to complete the booking."
            )
            return []

        ref = 'ARM-' + ''.join(random.choices(string.digits, k=4))

        try:
            conn = sqlite3.connect('database/aroma.db')
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reservations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ref TEXT UNIQUE, name TEXT, phone TEXT, email TEXT,
                    date TEXT, time TEXT, guests TEXT, special_req TEXT,
                    status TEXT DEFAULT "Confirmed",
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute(
                'INSERT INTO reservations (ref, name, date, time, guests) VALUES (?,?,?,?,?)',
                (ref, name, date, time, guests)
            )
            conn.commit()
            conn.close()

            dispatcher.utter_message(text=(
                f"✅ **Table Reserved at Aroma & Co.!**\n\n"
                f"📋 Reference : {ref}\n"
                f"👤 Name      : {name}\n"
                f"📅 Date      : {date}\n"
                f"🕐 Time      : {time}\n"
                f"👥 Guests    : {guests}\n\n"
                f"We look forward to welcoming you! ☕\n"
                f"To cancel or modify, share your ref here or call +91 98765 43210."
            ))

        except Exception as e:
            logger.error(f"Reservation error: {e}")
            dispatcher.utter_message(text="Couldn't save your reservation. Please call +91 98765 43210.")

        return [
            SlotSet("customer_name", None), SlotSet("booking_date", None),
            SlotSet("booking_time", None),  SlotSet("guest_count", None),
        ]


# ═══════════════════════════════════════════════════════════════
#  SECTION 2 — SLOT AVAILABILITY CHECK
# ═══════════════════════════════════════════════════════════════

class ActionCheckSlots(Action):
    def name(self) -> Text:
        return "action_check_slots"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        date         = tracker.get_slot("booking_date")
        ALL_SLOTS    = ["8:00 AM","9:30 AM","11:00 AM","12:30 PM",
                        "2:00 PM","3:30 PM","5:00 PM","6:30 PM","8:00 PM"]
        MAX_PER_SLOT = 4

        if not date:
            dispatcher.utter_message(
                text="Our daily slots: " + "  •  ".join(ALL_SLOTS) +
                     "\n\nTell me your preferred date and I'll check live availability!"
            )
            return []

        try:
            conn = sqlite3.connect('database/aroma.db')
            cursor = conn.cursor()
            cursor.execute(
                "SELECT time, COUNT(*) FROM reservations "
                "WHERE date=? AND status!='Cancelled' GROUP BY time", (date,)
            )
            booked = {row[0]: row[1] for row in cursor.fetchall()}
            conn.close()

            available = [s for s in ALL_SLOTS if booked.get(s, 0) < MAX_PER_SLOT]
            full      = [s for s in ALL_SLOTS if booked.get(s, 0) >= MAX_PER_SLOT]

            if available:
                msg = f"Available slots on **{date}**:\n" + \
                      "\n".join(f"  ✅ {s}" for s in available)
                if full:
                    msg += "\n\nFully booked:\n" + "\n".join(f"  ❌ {s}" for s in full)
                msg += "\n\nWhich time works best for you?"
            else:
                msg = f"All slots on {date} are fully booked. 😔\nWould you like to try another date?"

            dispatcher.utter_message(text=msg)
        except Exception:
            dispatcher.utter_message(
                text="Available slots: 8 AM, 9:30 AM, 12:30 PM, 3:30 PM, 5 PM, 8 PM."
            )
        return []


# ═══════════════════════════════════════════════════════════════
#  SECTION 3 — CANCEL RESERVATION
# ═══════════════════════════════════════════════════════════════

class ActionCancelReservation(Action):
    def name(self) -> Text:
        return "action_cancel_reservation"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        ref = tracker.get_slot("booking_ref")

        if not ref:
            dispatcher.utter_message(
                text="Please share your booking reference (e.g. ARM-1234) and I'll cancel it right away."
            )
            return []

        try:
            conn = sqlite3.connect('database/aroma.db')
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE reservations SET status='Cancelled' WHERE ref=?", (ref.upper(),)
            )
            conn.commit()
            affected = cursor.rowcount
            conn.close()

            if affected:
                dispatcher.utter_message(text=(
                    f"✅ Reservation **{ref.upper()}** cancelled.\n"
                    f"We hope to see you another time! ☕"
                ))
            else:
                dispatcher.utter_message(text=(
                    f"No reservation found with ref **{ref}**.\n"
                    f"Please double-check or call +91 98765 43210."
                ))
        except Exception as e:
            logger.error(f"Cancel error: {e}")
            dispatcher.utter_message(text="Unable to cancel right now. Please call +91 98765 43210.")

        return [SlotSet("booking_ref", None)]


# ═══════════════════════════════════════════════════════════════
#  SECTION 4 — MENU INFO (Gemini-enhanced)
# ═══════════════════════════════════════════════════════════════

CAFE_MENU = {
    "espresso":       ("☕ Espresso Classico",         "₹120",  "Pure bold 25ml shot, Ethiopian blend."),
    "latte":          ("🥛 Signature Latte",            "₹220",  "Velvety microfoam over double ristretto. Bestseller."),
    "cold brew":      ("❄️ Cold Brew Reserve",          "₹280",  "18-hour slow-steeped Colombian over large ice."),
    "flat white":     ("🍯 Honey Cardamom Flat White",  "₹260",  "Spiced, golden and comforting."),
    "matcha":         ("🌿 Matcha Cortado",             "₹290",  "Ceremonial matcha meets espresso."),
    "mocha":          ("🍫 Dark Mocha",                 "₹250",  "72% Valrhona cocoa with house espresso."),
    "croissant":      ("🥐 Butter Croissant",           "₹160",  "French-style, laminated 27 times."),
    "truffle":        ("🥪 Truffle Mushroom Toast",     "₹380",  "Sourdough, ricotta, mushrooms & black truffle oil."),
    "grain bowl":     ("🥗 Seasonal Grain Bowl",        "₹350",  "Farro, roasted veggies, tahini. Vegan."),
    "eggs benedict":  ("🍳 Eggs Benedict",              "₹420",  "Poached eggs, hollandaise, smoked salmon on brioche."),
    "banana cake":    ("🧁 Brown Butter Banana Cake",   "₹290",  "Warm slice with vanilla bean gelato."),
    "charcuterie":    ("🧀 Cheese & Charcuterie Board", "₹680",  "Seasonal selection, house preserves, crackers."),
    "rose latte":     ("🌸 Rose Saffron Latte",         "₹320",  "Saffron milk, rose water & pistachio. Lucknow special."),
    "espresso tonic": ("🧊 Espresso Tonic",             "₹300",  "Double shot over tonic, lemon peel. Effervescent."),
    "masala":         ("🍂 Masala Spice Brew",          "₹220",  "Single origin coffee with fresh desi spice blend."),
    "blueberry":      ("🫐 Blueberry Lavender Latte",   "₹310",  "Blueberry compote, lavender, oat milk over ice."),
    "hojicha":        ("🍵 Hojicha Latte",              "₹280",  "Roasted Japanese green tea. Perfect for evenings."),
    "brunch set":     ("🎂 Celebration Brunch Set",     "₹1,200","Curated spread for two."),
    "lemonade":       ("🍋 Sparkling Lemonade",         "₹180",  "House-pressed lemons, cane sugar, Perrier."),
    "berry cooler":   ("🍓 Summer Berry Cooler",        "₹220",  "Strawberry, raspberry, mint, elderflower over ice."),
    "mango lassi":    ("🥭 Alphonso Mango Lassi",       "₹200",  "Real Alphonso mangoes blended with yoghurt."),
    "mango":          ("🥭 Alphonso Mango Lassi",       "₹200",  "Real Alphonso mangoes blended with yoghurt."),
    "darjeeling":     ("🍵 Single Estate Darjeeling",   "₹160",  "First flush, delicate muscatel notes."),
    "kombucha":       ("🍺 House Kombucha",             "₹240",  "Ginger-lemon, brewed in-house. Gut-friendly."),
}


class ActionMenuInfo(Action):
    def name(self) -> Text:
        return "action_menu_info"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        product_name = tracker.get_slot("product_name")

        if not product_name:
            dispatcher.utter_message(text=(
                "Here's our menu:\n\n"
                "☕ **Coffee**   — ₹120 to ₹290\n"
                "🥐 **Food**     — ₹160 to ₹680\n"
                "🌸 **Specials** — Rose Saffron Latte, Espresso Tonic & more\n"
                "🍹 **Drinks**   — ₹160 to ₹240\n\n"
                "Ask me about any item for price and details! 😊"
            ))
            return []

        key   = product_name.lower()
        match = next((v for k, v in CAFE_MENU.items() if k in key or key in k), None)

        if match:
            name, price, desc = match
            # Use Gemini for a richer description
            gemini_reply = get_gemini_response(
                f"Describe our menu item '{name}' ({price}) in 2-3 engaging sentences. "
                f"Base info: {desc}. Make it sound appetizing and welcoming."
            )
            if gemini_reply:
                dispatcher.utter_message(text=f"{name} — **{price}**\n\n{gemini_reply}")
            else:
                dispatcher.utter_message(text=(
                    f"{name}\n💰 {price}\n📝 {desc}\n\nWant to reserve a table? 😊"
                ))
        else:
            # Unknown item — ask Gemini
            gemini_reply = get_gemini_response(
                f"User asked about '{product_name}'. If it's not on our menu, "
                f"say so politely and suggest the closest item we do have."
            )
            if gemini_reply:
                dispatcher.utter_message(text=gemini_reply)
            else:
                dispatcher.utter_message(text=(
                    f"I don't have '{product_name}' on our menu right now.\n"
                    f"Try: espresso, latte, cold brew, croissant, grain bowl, rose latte, kombucha!"
                ))

        return [SlotSet("product_name", None)]


# ═══════════════════════════════════════════════════════════════
#  SECTION 5 — CAFÉ INFO (Gemini for unknown questions)
# ═══════════════════════════════════════════════════════════════

class ActionCafeInfo(Action):
    def name(self) -> Text:
        return "action_cafe_info"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        text = tracker.latest_message.get('text', '').lower()

        if any(w in text for w in ['hour','open','timing','time','close','when']):
            msg = ("🕐 **Opening Hours:**\nMon–Fri: 8AM–10PM\nSat–Sun: 8AM–11PM\n"
                   "Last orders 30 min before closing.")
        elif any(w in text for w in ['where','location','address','direction','find','map']):
            msg = "📍 12-A Hazratganj, Lucknow – 226 001\nParking at Hazratganj Complex (2-min walk)."
        elif any(w in text for w in ['wifi','wi-fi','internet','password','network']):
            msg = "📶 Network: AromaCo_Guests\nPassword: coffeeislife ☕💻"
        elif any(w in text for w in ['park','parking','car']):
            msg = "🚗 Hazratganj Parking Complex, 2-minute walk from us."
        elif any(w in text for w in ['event','jazz','music','workshop','barista','live']):
            msg = ("🎷 Live Jazz — Fri & Sat, 7–10 PM\n"
                   "☕ Barista Workshop — Sundays, 10 AM (₹799)\n"
                   "🎂 Private Events — up to 30 guests")
        elif any(w in text for w in ['vegan','vegetarian','gluten','dairy','allerg','oat milk','diet']):
            msg = ("🌿 Vegan items available\n✅ Gluten-free on request\n"
                   "✅ Oat, almond & soy milk available")
        elif any(w in text for w in ['payment','pay','card','upi','cash']):
            msg = "💳 Cards, UPI, and cash accepted."
        elif any(w in text for w in ['contact','phone','call','email','reach']):
            msg = "📞 +91 8303920943\n📧 rohit@aromaandco.in"
        else:
            # Unknown question → Gemini handles it
            gemini_reply = get_gemini_response(tracker.latest_message.get('text', ''))
            if gemini_reply:
                dispatcher.utter_message(text=gemini_reply)
                return []
            msg = ("📍 12-A Hazratganj, Lucknow\n🕐 8AM–10PM (Mon–Fri) | 8AM–11PM (Sat–Sun)\n"
                   "📞 +91 8303920943\n📶 WiFi: AromaCo_Guests | coffeeislife")

        dispatcher.utter_message(text=msg)
        return []


# ═══════════════════════════════════════════════════════════════
#  SECTION 6 — GEMINI FALLBACK (core accuracy booster)
# ═══════════════════════════════════════════════════════════════

class ActionGeminiFallback(Action):
    """
    The KEY action for accuracy improvement.
    Triggered when Rasa confidence < 0.3 (FallbackClassifier).
    Sends message to Gemini with full café context.
    """

    def name(self) -> Text:
        return "action_gemini_fallback"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        user_message = tracker.latest_message.get("text", "")

        if not user_message:
            dispatcher.utter_message(text="I didn't catch that. Could you rephrase? 😊")
            return []

        logger.info(f"[Gemini Fallback] triggered for: '{user_message}'")

        gemini_reply = get_gemini_response(user_message)

        if gemini_reply:
            dispatcher.utter_message(text=gemini_reply)
        else:
            dispatcher.utter_message(text=(
                "I'm not sure about that, but I can help with:\n\n"
                "📅 Table reservations\n"
                "☕ Menu & prices\n"
                "🕐 Opening hours & location\n"
                "🎷 Events & workshops\n"
                "👤 Connect to our team\n\n"
                "What would you like? 😊"
            ))

        return []


# ═══════════════════════════════════════════════════════════════
#  SECTION 7 — FREE GEMINI CHAT (chitchat, recommendations)
# ═══════════════════════════════════════════════════════════════

class ActionGeminiChat(Action):
    """
    Handles chitchat, compliments, open-ended questions,
    coffee recommendations, and anything conversational.
    """

    def name(self) -> Text:
        return "action_gemini_chat"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        user_message = tracker.latest_message.get("text", "")

        gemini_reply = get_gemini_response(user_message)

        if gemini_reply:
            dispatcher.utter_message(text=gemini_reply)
        else:
            dispatcher.utter_message(text=(
                "That's interesting! I'm best at helping with café bookings, "
                "menu questions, and event info. What can I help you with? ☕"
            ))

        return []


# ═══════════════════════════════════════════════════════════════
#  SECTION 8 — HUMAN ESCALATION
# ═══════════════════════════════════════════════════════════════

class ActionHumanHandoff(Action):
    def name(self) -> Text:
        return "action_human_handoff"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(text=(
            "👤 **Connecting you to our team...**\n\n"
            f"Session ID : CHT-{tracker.sender_id[:8].upper()}\n\n"
            "📞 +91 8303920943\n"
            "📧 rohit@aromaandco.in\n\n"
            "A team member will be with you shortly. Avg. wait: 2–3 minutes."
        ))
        return []


# ═══════════════════════════════════════════════════════════════
#  SECTION 9 — FORM VALIDATOR
# ═══════════════════════════════════════════════════════════════

class ValidateReservationForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_reservation_form"

    def validate_booking_date(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict,
    ) -> Dict[Text, Any]:
        if slot_value:
            return {"booking_date": slot_value}
        dispatcher.utter_message(text="Please provide a valid date (e.g. 'tomorrow' or '25 March').")
        return {"booking_date": None}

    def validate_guest_count(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict,
    ) -> Dict[Text, Any]:
        try:
            n = int(str(slot_value).strip().split()[0])
            if 1 <= n <= 20:
                return {"guest_count": str(n)}
            dispatcher.utter_message(text="We accommodate 1–20 guests. How many in your group?")
            return {"guest_count": None}
        except (ValueError, IndexError):
            dispatcher.utter_message(text="How many guests will be joining you?")
            return {"guest_count": None}