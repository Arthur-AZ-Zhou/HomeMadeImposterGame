import os
import random
import time
from flask import Flask, render_template, request, jsonify, session
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('app_secret_key', 'super_secret_local_key')

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel("gemini-flash-latest")

GAME_STATE = {
    "status": "lobby",
    "players": [], 
    "imposter": "",
    "category": "",
    "word": "",
    "last_updated": time.time()
}



def gemini_api_call(category):
    try:
        # UPDATED STRATEGY: 
        # 1. Ask for a list of 12 items to prevent getting the same "top result" every time.
        # 2. Added "unexpected or funny" to the prompt to spice up the variety.
        prompt = (
            f"I need a variety of options for the party game 'Imposter'. "
            f"Give me a list of 12 distinct examples of '{category}'. "
            f"Include a mix of popular options and some unexpected or funny ones. "
            f"Respond with ONLY the words separated by commas. "
            f"Do not use numbering or bullet points. "
            f"Example output: Apple, Banana, Dragonfruit, Durian"
        )

        # 1. Get the list from Gemini
        response = model.generate_content(prompt)
        text_response = response.text.strip()
        
        # 2. Clean and Parse: Split by comma, remove extra spaces/newlines
        options = [word.strip() for word in text_response.split(',') if word.strip()]
        
        # 3. Fallback: If Gemini ignores instructions and gives empty list
        if not options:
            return "Error: No words found"
            
        # 4. Pick a random winner locally
        # SystemRandom ensures high-quality randomness
        secure_random = random.SystemRandom()
        chosen_word = secure_random.choice(options)
        
        # Debugging: Print options to terminal so you can see what Gemini gave
        print(f"DEBUG: Category '{category}' -> Options: {options}")
        print(f"DEBUG: Winner: {chosen_word}")
        
        return chosen_word

    except Exception as e:
        print(f"Gemini Error: {e}")
        return "Apple" # Ultimate fallback



@app.route('/')
def index():
    return render_template('player.html')


@app.route('/host')
def host():
    return render_template('host.html')



@app.route('/api/join', methods=['POST'])
def join_game():
    data = request.json
    name = data.get('name', '').strip().upper()
    
    if not name:
        return jsonify({"error": "Name required"}), 400
    
    if name in GAME_STATE['players']:
        return jsonify({"error": "Name taken"}), 400
        
    GAME_STATE['players'].append(name)
    session['player_name'] = name
    return jsonify({"success": True, "name": name})



@app.route('/api/status', methods=['GET'])
def get_status():
    player_name = request.headers.get('X-Player-Name')
    
    response = {
        "status": GAME_STATE['status'],
        "players": GAME_STATE['players'],
        "player_count": len(GAME_STATE['players']),
        "category": GAME_STATE['category'],
        "role": "spectator"
    }
    
    if GAME_STATE['status'] == 'playing' and player_name:
        if player_name == GAME_STATE['imposter']:
            response['role'] = 'imposter'
            response['secret_word'] = "???" 
        elif player_name in GAME_STATE['players']:
            response['role'] = 'civilian'
            response['secret_word'] = GAME_STATE['word']
            
    return jsonify(response)


@app.route('/api/start', methods=['POST'])
def start_game():
    data = request.json
    category = data.get('category')
    
    if len(GAME_STATE['players']) < 2:
        return jsonify({"error": "Need at least 2 players"}), 400

    word = gemini_api_call(category)
    imposter = random.choice(GAME_STATE['players'])

    print(f"DEBUG: The Imposter is {imposter}")
    
    GAME_STATE['status'] = 'playing'
    GAME_STATE['category'] = category
    GAME_STATE['word'] = word
    GAME_STATE['imposter'] = imposter
    
    return jsonify({"success": True, "word": word})

@app.route('/api/reset', methods=['POST'])


def reset_game():
    GAME_STATE['status'] = 'lobby'
    GAME_STATE['players'] = []
    GAME_STATE['imposter'] = ""
    GAME_STATE['category'] = ""
    GAME_STATE['word'] = ""
    return jsonify({"success": True})



if __name__ == '__main__':
    app.run(debug=True, port=5000)