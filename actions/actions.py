# This files contains your custom actions which can be used to run
# custom Python code.
#
# See this guide on how to implement these action:
# https://rasa.com/docs/rasa/custom-actions


# This is a simple example for a custom action which utters "Hello World!"

# from typing import Any, Text, Dict, List
#
# from rasa_sdk import Action, Tracker
# from rasa_sdk.executor import CollectingDispatcher
#
#
# class ActionHelloWorld(Action):
#
#     def name(self) -> Text:
#         return "action_hello_world"
#
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#
#         dispatcher.utter_message(text="Hello World!")
#
#         return []

from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict
from rasa_sdk.events import SlotSet
import sqlite3
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ActionCheckOrderStatus(Action):
    def name(self) -> Text:
        return "action_check_order_status"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        order_id = tracker.get_slot("order_id")
        
        if not order_id:
            dispatcher.utter_message(text="Please provide your order ID.")
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
                message = f"""
📦 **Order Details:**
- Order ID: {oid}
- Product: {product}
- Status: {status}
- Expected Delivery: {delivery}
- Tracking: {tracking}

Your order is on its way! 🚚
                """
                dispatcher.utter_message(text=message)
            else:
                dispatcher.utter_message(
                    text=f"Sorry, I couldn't find order {order_id}. Please check the order ID and try again."
                )
            
        except Exception as e:
            logger.error(f"Error checking order: {e}")
            dispatcher.utter_message(text="Sorry, I'm having trouble accessing order information right now.")
        
        return [SlotSet("order_id", None)]


class ActionProductInfo(Action):
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
            
            # Fuzzy search
            cursor.execute('''
                SELECT name, price, stock, description
                FROM products WHERE LOWER(name) LIKE ?
            ''', (f'%{product_name.lower()}%',))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                name, price, stock, desc = result
                message = f"""
🛍️ **{name}**
💰 Price: {price}
📦 Stock: {stock}
📝 {desc}

Would you like to know anything else?
                """
                dispatcher.utter_message(text=message)
            else:
                dispatcher.utter_message(
                    text=f"Sorry, I couldn't find information about '{product_name}'. Could you try another product?"
                )
            
        except Exception as e:
            logger.error(f"Error fetching product info: {e}")
            dispatcher.utter_message(text="Sorry, I'm having trouble accessing product information.")
        
        return [SlotSet("product_name", None)]


class ActionSubmitReturn(Action):
    def name(self) -> Text:
        return "action_submit_return"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        order_id = tracker.get_slot("order_id")
        reason = tracker.get_slot("return_reason")
        action = tracker.get_slot("preferred_action")
        
        # Save to database (for demonstration)
        try:
            conn = sqlite3.connect('database/orders.db')
            cursor = conn.cursor()
            
            # Create returns table if not exists
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS returns (
                    return_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT,
                    reason TEXT,
                    preferred_action TEXT,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                INSERT INTO returns (order_id, reason, preferred_action, status)
                VALUES (?, ?, ?, ?)
            ''', (order_id, reason, action, 'Pending'))
            
            return_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            message = f"""
✅ **Return Request Submitted**
- Return ID: RET{return_id:05d}
- Order ID: {order_id}
- Reason: {reason}
- Action: {action}

We'll process your request within 24 hours. You'll receive an email confirmation shortly.
            """
            dispatcher.utter_message(text=message)
            
        except Exception as e:
            logger.error(f"Error submitting return: {e}")
            dispatcher.utter_message(text="Sorry, couldn't submit your return request. Please try again.")
        
        return [
            SlotSet("order_id", None),
            SlotSet("return_reason", None),
            SlotSet("preferred_action", None)
        ]


class ValidateReturnForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_return_form"

    def validate_order_id(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        
        # Check if order exists
        try:
            conn = sqlite3.connect('database/orders.db')
            cursor = conn.cursor()
            cursor.execute('SELECT order_id FROM orders WHERE order_id = ?', (slot_value,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {"order_id": slot_value}
            else:
                dispatcher.utter_message(text="I couldn't find that order ID. Please check and try again.")
                return {"order_id": None}
        except:
            return {"order_id": slot_value}  # Allow it for demo purposes


class ActionHumanHandoff(Action):
    def name(self) -> Text:
        return "action_human_handoff"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        message = """
👤 **Connecting you to a human agent...**

While you wait, here's your chat transcript ID: CHT-{id}

An agent will be with you shortly. Average wait time: 2-3 minutes.
        """.format(id=tracker.sender_id[:8])
        
        dispatcher.utter_message(text=message)
        
        return []