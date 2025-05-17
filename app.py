from flask import Flask, render_template, request, jsonify, session
import requests
import uuid
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)

# API Configuration
API_KEY = "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"
MODEL = "deepseek/deepseek-chat-v3-0324:free"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

# Initialize session variables if they don't exist
@app.before_request
def before_request():
    if 'chats' not in session:
        session['chats'] = {}
    if 'current_chat_id' not in session:
        new_chat_id = str(uuid.uuid4())
        session['current_chat_id'] = new_chat_id
        session['chats'][new_chat_id] = {
            'title': f"Travel Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            'messages': []
        }
        session.modified = True

@app.route('/')
def index():
    # Sort chats with most recent first
    sorted_chats = {k: v for k, v in sorted(
        session['chats'].items(),
        key=lambda item: item[0],  # Sort by chat_id which correlates with creation time
        reverse=True  # Reverse to get newest first
    )}
    
    return render_template('index.html', 
                          chats=sorted_chats, 
                          current_chat_id=session['current_chat_id'])

@app.route('/new_chat', methods=['POST'])
def new_chat():
    new_chat_id = str(uuid.uuid4())
    session['current_chat_id'] = new_chat_id
    session['chats'][new_chat_id] = {
        'title': f"Travel Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        'messages': []
    }
    session.modified = True
    return jsonify({
        'chat_id': new_chat_id,
        'title': session['chats'][new_chat_id]['title']
    })

@app.route('/switch_chat/<chat_id>', methods=['POST'])
def switch_chat(chat_id):
    if chat_id in session['chats']:
        session['current_chat_id'] = chat_id
        session.modified = True
        return jsonify({
            'chat_id': chat_id,
            'messages': session['chats'][chat_id]['messages']
        })
    return jsonify({'error': 'Chat not found'}), 404

@app.route('/send_message', methods=['POST'])
def send_message():
    user_message = request.json.get('message', '')
    chat_id = session['current_chat_id']
    
    if not user_message:
        return jsonify({'error': 'Message cannot be empty'}), 400
    
    # Add user message to chat history
    session['chats'][chat_id]['messages'].append({
        'role': 'user',
        'content': user_message
    })
    session.modified = True
    
    # Travel-related keywords to check in user input
    travel_keywords = [
        "travel", "trip", "vacation", "holiday", "destination", "tour", "flight", "hotel", 
        "resort", "booking", "accommodation", "itinerary", "sightseeing", "tourist", 
        "attraction", "beach", "mountain", "hiking", "camping", "backpacking", "road trip",
        "cruise", "adventure", "explore", "visit", "country", "city", "island", "landmark",
        "culture", "museum", "restaurant", "food", "cuisine", "local", "guide", "map",
        "transport", "train", "bus", "car rental", "airport", "airline", "luggage", "pack",
        "visa", "passport", "currency", "exchange", "budget", "cost", "expense", "cheap",
        "luxury", "weather", "season", "summer", "winter", "spring", "fall", "autumn",
        "photography", "souvenir", "shopping", "wifi", "language", "translate", "safety",
        "insurance", "emergency", "time zone", "jet lag", "ticket", "reservation", "go to",
        "visit", "see", "do", "experience", "enjoy", "relax", "fun", "adventure", "exploration",
        "nature", "wildlife", "scenery", "landscape", "view", "sunset", "sunrise", "trains",
        "airports","flights", "buses", "cars", "taxis", "rideshare", "public transport", "local transport", "local transport",
    ]
    
    # Check if the message contains travel-related keywords
    is_travel_related = any(keyword in user_message.lower() for keyword in travel_keywords)
    
    # Create system prompt based on message content
    if is_travel_related:
        system_content = "You are a specialized travel assistant chatbot that provides information about destinations, itineraries, accommodations, transportation, travel tips, local cuisine, cultural customs, visa requirements, travel gear, weather conditions, and tourist attractions. Format your responses with clear headings using '### Heading', use bullet points with dashes (- item) for lists, and use **text** for emphasis. Structure your information in well-organized sections. Keep responses concise, informative, and engaging."
    else:
        system_content = "You are a specialized travel assistant chatbot. Politely inform the user that you can only assist with travel-related questions and provide examples of topics you can help with, such as destination recommendations, itineraries, accommodations, transportation, travel tips, local cuisine, cultural customs, visa requirements, travel gear, weather conditions, and tourist attractions. Format your response with headings and bullet points."
    
    # Create messages for API request including chat history
    messages = [
        {"role": "system", "content": system_content},
    ]
    
    # Add conversation history
    for msg in session['chats'][chat_id]['messages']:
        messages.append({"role": msg['role'], "content": msg['content']})
    
    # Make API request
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL,
        "messages": messages
    }
    
    try:
        response = requests.post(ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        
        ai_message = response.json()['choices'][0]['message']['content']
        
        # Add AI response to chat history - store the raw, unformatted content
        session['chats'][chat_id]['messages'].append({
            'role': 'assistant',
            'content': ai_message
        })
        session.modified = True
        
        return jsonify({
            'response': ai_message,
            'messages': session['chats'][chat_id]['messages']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete_chat/<chat_id>', methods=['POST'])
def delete_chat(chat_id):
    if chat_id not in session['chats']:
        return jsonify({'success': False, 'error': 'Chat not found'}), 404
    
    was_current = (chat_id == session['current_chat_id'])
    
    # Delete the chat
    del session['chats'][chat_id]
    
    # If the deleted chat was the current one, set a new current chat if any exist
    if was_current:
        if session['chats']:
            session['current_chat_id'] = next(iter(session['chats'].keys()))
        else:
            # If no chats remain, create a new one
            new_chat_id = str(uuid.uuid4())
            session['current_chat_id'] = new_chat_id
            session['chats'][new_chat_id] = {
                'title': f"Travel Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                'messages': []
            }
    
    session.modified = True
    
    return jsonify({
        'success': True, 
        'was_current': was_current
    })

if __name__ == '__main__':
    app.run(debug=True)
