# =============================================================
#  actions/actions.py
#  Aroma & Co. — Customer Support Chatbot (Rasa SDK)
#  Covers:
#    Section 1 — E-commerce: order tracking, product info, returns
#    Section 2 — Café: table reservation, slot checking, cancellation
#    Section 3 — Café: menu info, general café info
#    Section 4 — Shared: human agent escalation
#    Section 5 — Form validators
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  SECTION 1 — E-COMMERCE CUSTOMER SUPPORT
# ═══════════════════════════════════════════════════════════════

class ActionCheckOrderStatus(Action):
    """Track an order by order_id from the orders database."""

    def name(self) -> Text:
        return "action_check_order_status"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        order_id = tracker.get_slot("order_id")

        if not order_id:
            dispatcher.utter_message(
                text="Please provide your Order ID so I can look it up. "
                     "It looks like '12345' or 'ORD001'. 📦"
            )
            return []

        try:
            conn = sqlite3.connect('database/orders.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT order_id, product, status, expected_delivery, tracking_number
                FROM orders WHERE order_id = ?
            ''', (order_id,))
            result = cursor.fetchone()
            conn.close()

            if result:
                oid, product, status, delivery, tracking = result
                message = (
                    f"📦 **Order Details**\n\n"
                    f"• Order ID       : {oid}\n"
                    f"• Product        : {product}\n"
                    f"• Status         : {status}\n"
                    f"• Expected By    : {delivery}\n"
                    f"• Tracking No.   : {tracking}\n\n"
                    f"Your order is on its way! 🚚\n"
                    f"Is there anything else I can help you with?"
                )
            else:
                message = (
                    f"I couldn't find order **{order_id}**.\n\n"
                    f"Please double-check the ID — it should look like "
                    f"'12345' or 'ORD001'. If the issue persists, I can connect you to a human agent."
                )

            dispatcher.utter_message(text=message)

        except Exception as e:
            logger.error(f"Order lookup error: {e}")
            dispatcher.utter_message(
                text="I'm having trouble reaching the order system right now. "
                     "Please try again in a moment or call +91 98765 43210."
            )

        return [SlotSet("order_id", None)]


class ActionProductInfo(Action):
    """Fetch product price, stock, and description from the products database."""

    def name(self) -> Text:
        return "action_product_info"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        product_name = tracker.get_slot("product_name")

        if not product_name:
            dispatcher.utter_message(text="Which product would you like to know about?")
            return []

        try:
            conn = sqlite3.connect('database/products.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT name, price, stock, description
                FROM products WHERE LOWER(name) LIKE ?
            ''', (f'%{product_name.lower()}%',))
            result = cursor.fetchone()
            conn.close()

            if result:
                name, price, stock, desc = result
                stock_icon = "✅" if "In Stock" in stock else "⚠️"
                message = (
                    f"🛍️ **{name}**\n\n"
                    f"💰 Price   : {price}\n"
                    f"{stock_icon} Stock   : {stock}\n"
                    f"📝 Details : {desc}\n\n"
                    f"Would you like to place an order or need more info?"
                )
            else:
                message = (
                    f"I couldn't find a product matching '{product_name}'.\n"
                    f"Try searching by brand or model — e.g. 'iPhone 15' or 'Sony headphones'."
                )

            dispatcher.utter_message(text=message)

        except Exception as e:
            logger.error(f"Product info error: {e}")
            dispatcher.utter_message(
                text="Having trouble fetching product details right now. Please try again shortly."
            )

        return [SlotSet("product_name", None)]


class ActionSubmitReturn(Action):
    """Process a return/refund request and store it in the database."""

    def name(self) -> Text:
        return "action_submit_return"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        order_id      = tracker.get_slot("order_id")
        reason        = tracker.get_slot("return_reason")
        preferred_act = tracker.get_slot("preferred_action")

        try:
            conn = sqlite3.connect('database/orders.db')
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS returns (
                    return_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id         TEXT,
                    reason           TEXT,
                    preferred_action TEXT,
                    status           TEXT DEFAULT "Pending",
                    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                INSERT INTO returns (order_id, reason, preferred_action)
                VALUES (?, ?, ?)
            ''', (order_id, reason, preferred_act))

            return_id = cursor.lastrowid
            conn.commit()
            conn.close()

            message = (
                f"✅ **Return Request Submitted**\n\n"
                f"• Return ID  : RET{return_id:05d}\n"
                f"• Order ID   : {order_id}\n"
                f"• Reason     : {reason}\n"
                f"• Resolution : {preferred_act}\n\n"
                f"We'll process your request within 24 hours. "
                f"You'll receive an email confirmation shortly.\n\n"
                f"Is there anything else I can help with?"
            )
            dispatcher.utter_message(text=message)

        except Exception as e:
            logger.error(f"Return submission error: {e}")
            dispatcher.utter_message(
                text="Couldn't submit your return right now. "
                     "Please try again or call our support line."
            )

        return [
            SlotSet("order_id",         None),
            SlotSet("return_reason",    None),
            SlotSet("preferred_action", None),
        ]


class ValidateReturnForm(FormValidationAction):
    """Validate the return form — confirms the order exists before proceeding."""

    def name(self) -> Text:
        return "validate_return_form"

    def validate_order_id(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        try:
            conn = sqlite3.connect('database/orders.db')
            cursor = conn.cursor()
            cursor.execute(
                'SELECT order_id FROM orders WHERE order_id = ?', (slot_value,)
            )
            result = cursor.fetchone()
            conn.close()

            if result:
                return {"order_id": slot_value}
            dispatcher.utter_message(
                text=f"I couldn't find order **{slot_value}**. Please check and try again."
            )
            return {"order_id": None}

        except Exception:
            return {"order_id": slot_value}   # allow in demo if DB is unavailable


# ═══════════════════════════════════════════════════════════════
#  SECTION 2 — CAFÉ TABLE RESERVATION
# ═══════════════════════════════════════════════════════════════

class ActionReserveTable(Action):
    """Book a café table and persist to the reservations table."""

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
            conn = sqlite3.connect('database/orders.db')
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reservations (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    ref         TEXT UNIQUE,
                    name        TEXT,
                    phone       TEXT,
                    email       TEXT,
                    date        TEXT,
                    time        TEXT,
                    guests      TEXT,
                    special_req TEXT,
                    status      TEXT DEFAULT "Confirmed",
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                INSERT INTO reservations (ref, name, date, time, guests)
                VALUES (?, ?, ?, ?, ?)
            ''', (ref, name, date, time, guests))

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
                f"To modify or cancel, call +91 98765 43210 or share your ref number here."
            ))

        except Exception as e:
            logger.error(f"Reservation error: {e}")
            dispatcher.utter_message(
                text="Couldn't save your reservation right now. Please call +91 98765 43210."
            )

        return [
            SlotSet("customer_name", None),
            SlotSet("booking_date",  None),
            SlotSet("booking_time",  None),
            SlotSet("guest_count",   None),
        ]


class ActionCheckSlots(Action):
    """Show available time slots for a given date."""

    def name(self) -> Text:
        return "action_check_slots"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        date = tracker.get_slot("booking_date")

        ALL_SLOTS    = ["8:00 AM", "9:30 AM", "11:00 AM", "12:30 PM",
                        "2:00 PM", "3:30 PM", "5:00 PM",  "6:30 PM", "8:00 PM"]
        MAX_PER_SLOT = 4

        if not date:
            dispatcher.utter_message(
                text="Our daily slots are:\n" +
                     "  •  ".join(ALL_SLOTS) +
                     "\n\nTell me your preferred date and I'll check live availability!"
            )
            return []

        try:
            conn = sqlite3.connect('database/orders.db')
            cursor = conn.cursor()
            cursor.execute(
                "SELECT time, COUNT(*) FROM reservations "
                "WHERE date=? AND status!='Cancelled' GROUP BY time",
                (date,)
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
                msg = (f"All slots on {date} are fully booked. 😔\n"
                       "Would you like to try a different date?")

            dispatcher.utter_message(text=msg)

        except Exception:
            dispatcher.utter_message(
                text="Available slots: 8 AM, 9:30 AM, 12:30 PM, 3:30 PM, 5 PM, 8 PM. "
                     "Which works for you?"
            )

        return []


class ActionCancelReservation(Action):
    """Cancel a café reservation by reference number."""

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
            conn = sqlite3.connect('database/orders.db')
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE reservations SET status='Cancelled' WHERE ref=?",
                (ref.upper(),)
            )
            conn.commit()
            affected = cursor.rowcount
            conn.close()

            if affected:
                dispatcher.utter_message(
                    text=f"✅ Reservation **{ref.upper()}** has been cancelled.\n"
                         f"We hope to see you another time! ☕"
                )
            else:
                dispatcher.utter_message(
                    text=f"No reservation found with ref **{ref}**.\n"
                         f"Please double-check or call +91 98765 43210."
                )

        except Exception as e:
            logger.error(f"Cancel error: {e}")
            dispatcher.utter_message(
                text="Unable to cancel right now. Please call +91 98765 43210."
            )

        return [SlotSet("booking_ref", None)]


# ═══════════════════════════════════════════════════════════════
#  SECTION 3 — CAFÉ MENU & GENERAL INFO
# ═══════════════════════════════════════════════════════════════

CAFE_MENU = {
    "espresso":       ("☕ Espresso Classico",         "₹120",  "Pure bold 25ml shot, Ethiopian blend."),
    "latte":          ("🥛 Signature Latte",            "₹220",  "Velvety microfoam over double ristretto. Our bestseller."),
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
    "masala":         ("🍂 Masala Spice Brew",          "₹220",  "Single origin with fresh desi spice blend."),
    "blueberry":      ("🫐 Blueberry Lavender Latte",   "₹310",  "Blueberry compote, lavender syrup, oat milk over ice."),
    "hojicha":        ("🍵 Hojicha Latte",              "₹280",  "Roasted Japanese green tea. Perfect for evenings."),
    "brunch set":     ("🎂 Celebration Brunch Set",     "₹1,200","Curated spread for two — coffee, food, dessert, juice."),
    "lemonade":       ("🍋 Sparkling Lemonade",         "₹180",  "House-pressed lemons, cane sugar, Perrier."),
    "berry cooler":   ("🍓 Summer Berry Cooler",        "₹220",  "Strawberry, raspberry, mint, elderflower over ice."),
    "mango lassi":    ("🥭 Alphonso Mango Lassi",       "₹200",  "Real Alphonso mangoes with yoghurt."),
    "mango":          ("🥭 Alphonso Mango Lassi",       "₹200",  "Real Alphonso mangoes with yoghurt."),
    "darjeeling":     ("🍵 Single Estate Darjeeling",   "₹160",  "First flush, delicate muscatel notes."),
    "kombucha":       ("🍺 House Kombucha",             "₹240",  "Ginger-lemon, brewed in-house. Gut-friendly."),
}


class ActionCafeMenuInfo(Action):
    """Answer café menu, price, and availability questions."""

    def name(self) -> Text:
        return "action_cafe_menu_info"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        product_name = tracker.get_slot("product_name")

        if not product_name:
            dispatcher.utter_message(text=(
                "Here's our menu at a glance:\n\n"
                "☕ **Coffee**   — Espresso (₹120) to Matcha Cortado (₹290)\n"
                "🥐 **Food**     — Croissant (₹160) to Charcuterie Board (₹680)\n"
                "🌸 **Specials** — Rose Saffron Latte, Espresso Tonic & more\n"
                "🍹 **Drinks**   — Lassi, Kombucha, Darjeeling from ₹160\n\n"
                "Ask me about any specific item for details and price!"
            ))
            return []

        key   = product_name.lower()
        match = next((v for k, v in CAFE_MENU.items() if k in key or key in k), None)

        if match:
            name, price, desc = match
            dispatcher.utter_message(text=(
                f"{name}\n"
                f"💰 Price  : {price}\n"
                f"📝 About  : {desc}\n\n"
                f"Would you like to reserve a table to try it? 😊"
            ))
        else:
            dispatcher.utter_message(text=(
                f"I don't have details for '{product_name}' right now.\n\n"
                f"Try asking about: espresso, latte, cold brew, croissant, "
                f"grain bowl, rose latte, mango lassi, and more!"
            ))

        return [SlotSet("product_name", None)]


class ActionCafeInfo(Action):
    """Answer hours, location, wifi, events, dietary, and payment questions."""

    def name(self) -> Text:
        return "action_cafe_info"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        text = tracker.latest_message.get('text', '').lower()

        if any(w in text for w in ['hour', 'open', 'timing', 'time', 'close', 'when']):
            msg = (
                "🕐 **Opening Hours:**\n"
                "Mon – Fri : 8:00 AM – 10:00 PM\n"
                "Sat – Sun : 8:00 AM – 11:00 PM\n\n"
                "Last orders 30 minutes before closing."
            )
        elif any(w in text for w in ['where', 'location', 'address', 'direction', 'find', 'map']):
            msg = (
                "📍 **Location:**\n"
                "12-A Hazratganj, Lucknow – 226 001\n\n"
                "Parking available at Hazratganj Complex (2-min walk)."
            )
        elif any(w in text for w in ['wifi', 'wi-fi', 'internet', 'password', 'network']):
            msg = (
                "📶 **Free WiFi:**\n"
                "Network  : AromaCo_Guests\n"
                "Password : coffeeislife\n\n"
                "Perfect for working remotely! ☕💻"
            )
        elif any(w in text for w in ['park', 'parking', 'car']):
            msg = "🚗 Parking is available at Hazratganj Parking Complex, just a 2-minute walk from us."
        elif any(w in text for w in ['event', 'jazz', 'music', 'workshop', 'barista', 'live']):
            msg = (
                "🎷 **Events at Aroma & Co.:**\n\n"
                "🎶 Live Jazz Night — Every Fri & Sat, 7–10 PM\n"
                "☕ Barista Workshop — Sundays, 10 AM (₹799/person)\n"
                "🎂 Private Events — Birthdays, off-sites up to 30 guests\n\n"
                "Would you like to book a spot or a table for an event?"
            )
        elif any(w in text for w in ['vegan', 'vegetarian', 'gluten', 'dairy', 'allerg', 'oat milk', 'diet']):
            msg = (
                "🌿 **Dietary Options:**\n"
                "✅ Vegan-friendly items available\n"
                "✅ Gluten-free alternatives on request\n"
                "✅ Oat milk, almond milk & soy milk available\n\n"
                "Just let your server know your requirements!"
            )
        elif any(w in text for w in ['payment', 'pay', 'card', 'upi', 'cash']):
            msg = "💳 We accept all major credit/debit cards, UPI, and cash."
        else:
            msg = (
                "Here's everything about **Aroma & Co.**:\n\n"
                "📍 12-A Hazratganj, Lucknow – 226 001\n"
                "🕐 Mon–Fri: 8AM–10PM  |  Sat–Sun: 8AM–11PM\n"
                "📞 +91 98765 43210\n"
                "📧 hello@aromaandco.in\n"
                "📶 WiFi: AromaCo_Guests | coffeeislife\n\n"
                "What else can I help you with?"
            )

        dispatcher.utter_message(text=msg)
        return []


# ═══════════════════════════════════════════════════════════════
#  SECTION 4 — SHARED: HUMAN AGENT ESCALATION
# ═══════════════════════════════════════════════════════════════

class ActionHumanHandoff(Action):
    """Escalate the conversation to a live support agent."""

    def name(self) -> Text:
        return "action_human_handoff"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(text=(
            "👤 **Connecting you to our support team...**\n\n"
            f"Session ID : CHT-{tracker.sender_id[:8].upper()}\n\n"
            "You can also reach us directly:\n"
            "📞 +91 98765 43210\n"
            "📧 support@aromaandco.in\n\n"
            "An agent will be with you shortly. Average wait: 2–3 minutes."
        ))
        return []


# ═══════════════════════════════════════════════════════════════
#  SECTION 5 — FORM VALIDATORS
# ═══════════════════════════════════════════════════════════════

class ValidateReservationForm(FormValidationAction):
    """Validate the café table reservation form."""

    def name(self) -> Text:
        return "validate_reservation_form"

    def validate_booking_date(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict,
    ) -> Dict[Text, Any]:
        if slot_value:
            return {"booking_date": slot_value}
        dispatcher.utter_message(
            text="Please provide a valid date (e.g. 'tomorrow' or '25 March')."
        )
        return {"booking_date": None}

    def validate_guest_count(
        self, slot_value: Any, dispatcher: CollectingDispatcher,
        tracker: Tracker, domain: DomainDict,
    ) -> Dict[Text, Any]:
        try:
            n = int(str(slot_value).strip().split()[0])
            if 1 <= n <= 20:
                return {"guest_count": str(n)}
            dispatcher.utter_message(
                text="We can accommodate 1–20 guests. How many are in your group?"
            )
            return {"guest_count": None}
        except (ValueError, IndexError):
            dispatcher.utter_message(text="How many guests will be joining you?")
            return {"guest_count": None}