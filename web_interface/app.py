from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

RASA_API_URL = "http://localhost:5005/webhooks/rest/webhook"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message')
    sender_id = request.json.get('sender', 'user')
    
    payload = {
        "sender": sender_id,
        "message": user_message
    }
    
    try:
        response = requests.post(RASA_API_URL, json=payload)
        bot_responses = response.json()
        return jsonify(bot_responses)
    except:
        return jsonify([{"text": "Sorry, I'm having trouble connecting."}])

if __name__ == '__main__':
    app.run(debug=True, port=8000)