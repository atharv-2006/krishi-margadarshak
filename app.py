from PIL import Image
import io
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import base64
import json
import requests as req
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = 'krishi_secret_key_2024'

def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

create_tables()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        try:
            conn = get_db()
            conn.execute(
                'INSERT INTO users (name, email, password) VALUES (?, ?, ?)',
                (name, email, hashed_password)
            )
            conn.commit()
            conn.close()
            flash('Account created successfully! Please login.', 'success')
            return redirect(url_for('login'))
        except:
            flash('Email already exists! Try a different one.', 'danger')
            return redirect(url_for('signup'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db()
        user = conn.execute(
            'SELECT * FROM users WHERE email = ?', (email,)
        ).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            flash('Welcome back, ' + user['name'] + '!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Wrong email or password. Try again.', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))
    return render_template('dashboard.html', name=session['user_name'])

@app.route('/crop', methods=['GET', 'POST'])
def crop():
    if 'user_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        season = request.form['season']
        soil = request.form['soil']
        water = request.form['water']
        budget = request.form['budget']
        farm_size = request.form['farm_size']
        previous_crop = request.form['previous_crop']

        prompt = f"""You are an expert Indian agricultural scientist.
A farmer has provided the following details:
- Season: {season}
- Soil Type: {soil}
- Water Availability: {water}
- Budget: {budget}
- Farm Size: {farm_size} acres
- Previous Crop Grown: {previous_crop}

Based on these details, provide a crop recommendation with exactly these sections:

1. BEST CROP TO GROW: (name the crop)
2. EXPECTED YIELD: (per acre)
3. ESTIMATED PROFIT: (in rupees per acre)
4. WATER REQUIREMENT: (low/medium/high and how often)
5. FERTILIZER NEEDED: (what type and how much)
6. GROWING DURATION: (how many days/months)

Keep it simple, practical and helpful for an Indian farmer."""

        try:
            nvidia_key = os.getenv('NVIDIA_API_KEY')
            response = req.post(
                'https://integrate.api.nvidia.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {nvidia_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'meta/llama-3.1-70b-instruct',
                    'messages': [
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ],
                    'max_tokens': 800,
                    'temperature': 0.3
                },
                timeout=60
            )
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                result = data['choices'][0]['message']['content']
            else:
                result = 'ERROR: ' + str(data)

        except Exception as e:
            result = "ERROR: " + str(e)

        return render_template('result.html',
                               result=result,
                               season=season,
                               soil=soil,
                               water=water,
                               budget=budget,
                               farm_size=farm_size,
                               previous_crop=previous_crop)

    return render_template('crop.html')

@app.route('/schemes')
def schemes():
    if 'user_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))
    return render_template('schemes.html')

@app.route('/problems')
def problems():
    if 'user_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))
    return render_template('problems.html')

def get_medicine_advice(label):
    label = label.lower()
    if 'healthy' in label:
        return {
            'medicines': ['No medicine needed — plant is healthy!'],
            'organic': ['Continue regular watering and fertilization'],
            'prevention': ['Keep monitoring regularly', 'Maintain proper spacing', 'Ensure good drainage']
        }
    elif 'blight' in label:
        return {
            'medicines': ['Mancozeb 75% WP — 2g per litre', 'Chlorothalonil 75% WP — 2g per litre', 'Metalaxyl + Mancozeb — 2.5g per litre'],
            'organic': ['Copper oxychloride spray 3g per litre', 'Neem oil 5ml per litre'],
            'prevention': ['Avoid overhead irrigation', 'Remove infected leaves immediately', 'Crop rotation every season']
        }
    elif 'rust' in label:
        return {
            'medicines': ['Propiconazole 25% EC — 1ml per litre', 'Tebuconazole 250 EW — 1ml per litre'],
            'organic': ['Sulfur dust application', 'Neem oil spray 5ml per litre'],
            'prevention': ['Use rust-resistant varieties', 'Early sowing', 'Avoid dense planting']
        }
    elif 'spot' in label or 'cercospora' in label:
        return {
            'medicines': ['Mancozeb 2g per litre', 'Carbendazim 50% WP — 1g per litre'],
            'organic': ['Neem oil 5ml per litre', 'Copper oxychloride spray'],
            'prevention': ['Crop rotation', 'Remove crop debris after harvest', 'Use certified seeds']
        }
    elif 'mildew' in label or 'powdery' in label:
        return {
            'medicines': ['Carbendazim 50% WP — 1g per litre', 'Sulfur 80% WP — 2g per litre'],
            'organic': ['Baking soda 1 spoon per litre water', 'Neem oil spray'],
            'prevention': ['Avoid excess nitrogen', 'Ensure good air circulation', 'Avoid wetting leaves']
        }
    elif 'virus' in label or 'mosaic' in label or 'curl' in label:
        return {
            'medicines': ['Imidacloprid 17.8% SL — 0.5ml per litre', 'Thiamethoxam 25 WG — 0.2g per litre'],
            'organic': ['Neem oil 5ml per litre', 'Yellow sticky traps for whiteflies'],
            'prevention': ['Remove and destroy infected plants', 'Control insects early', 'Use virus-resistant varieties']
        }
    elif 'rot' in label or 'scab' in label:
        return {
            'medicines': ['Carbendazim 1g per litre soil drench', 'Copper oxychloride 3g per litre'],
            'organic': ['Trichoderma viride soil application', 'Neem cake soil application'],
            'prevention': ['Avoid waterlogging', 'Improve soil drainage', 'Crop rotation']
        }
    elif 'bacterial' in label:
        return {
            'medicines': ['Streptocycline 500ppm spray', 'Copper oxychloride 3g per litre', 'Kasugamycin 3% SL — 2ml per litre'],
            'organic': ['Copper sulfate spray', 'Remove infected plant parts immediately'],
            'prevention': ['Use disease-free seeds', 'Avoid plant injuries', 'Maintain field hygiene']
        }
    else:
        return {
            'medicines': ['Mancozeb 75% WP — 2g per litre', 'Consult local agricultural officer'],
            'organic': ['Neem oil 5ml per litre', 'Copper oxychloride spray'],
            'prevention': ['Regular crop monitoring', 'Use certified seeds', 'Call Kisan Helpline: 1800-180-1551']
        }

@app.route('/ai-detector', methods=['GET', 'POST'])
def ai_detector():
    if 'user_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))

    result = None

    if request.method == 'POST':
        image_file = request.files['crop_image']

        if image_file:
            img = Image.open(image_file)
            img = img.convert('RGB')
            img = img.resize((512, 512))
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=90)
            image_data = buffer.getvalue()
            image_base64 = base64.b64encode(image_data).decode('utf-8')

            nvidia_key = os.getenv('NVIDIA_API_KEY')

            prompt = """You are an expert Indian agricultural scientist and plant pathologist.
Analyze this crop/plant image carefully and provide:

1. DISEASE OR PROBLEM DIAGNOSIS:
- What disease, pest, or problem do you see?
- How severe is it? (Mild / Moderate / Severe)
- Which crop/plant is affected?

2. RECOMMENDED MEDICINES AND TREATMENTS:
- Specific fungicides, pesticides, or treatments
- Dosage and application method
- Brand names available in India if possible

3. ORGANIC ALTERNATIVES:
- Natural or organic treatment options

4. PREVENTION TIPS:
- How to prevent this in future

If the plant looks completely healthy, clearly state that.
Keep response practical and helpful for an Indian farmer."""

            try:
                response = req.post(
                    'https://integrate.api.nvidia.com/v1/chat/completions',
                    headers={
                        'Authorization': f'Bearer {nvidia_key}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': 'meta/llama-3.2-11b-vision-instruct',
                        'messages': [
                            {
                                'role': 'user',
                                'content': [
                                    {
                                        'type': 'text',
                                        'text': prompt
                                    },
                                    {
                                        'type': 'image_url',
                                        'image_url': {
                                            'url': f'data:image/jpeg;base64,{image_base64}'
                                        }
                                    }
                                ]
                            }
                        ],
                        'max_tokens': 1024,
                        'temperature': 0.2
                    },
                    timeout=60
                )

                data = response.json()

                if 'choices' in data and len(data['choices']) > 0:
                    ai_response = data['choices'][0]['message']['content']
                    result = {
                        'status': 'success',
                        'analysis': ai_response
                    }
                elif 'error' in data:
                    result = {
                        'status': 'error',
                        'message': str(data['error'])
                    }
                else:
                    result = {
                        'status': 'error',
                        'message': 'Raw response: ' + str(data)
                    }

            except Exception as e:
                result = {
                    'status': 'error',
                    'message': str(e)
                }

    return render_template('ai_detector.html', result=result)

# ------------------------------------------------
# MARKET PRICE ADVISOR
# ------------------------------------------------
@app.route('/market', methods=['GET', 'POST'])
def market():
    if 'user_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))

    result = None

    if request.method == 'POST':
        crop = request.form['crop']
        quantity = request.form['quantity']
        location = request.form['location']
        quality = request.form['quality']
        harvest_date = request.form['harvest_date']

        prompt = f"""You are an expert Indian agricultural market analyst.

A farmer wants to sell:
- Crop: {crop}
- Quantity: {quantity} quintals
- Location: {location}
- Quality: {quality}
- Harvest Date: {harvest_date}

Give concise market advice with these sections:

1. CURRENT PRICE RANGE: (per quintal in India)
2. MARKET TREND: (rising/falling/stable and why)
3. BEST TIME TO SELL: (now or wait, with reason)
4. EXPECTED EARNINGS: (for {quantity} quintals)
5. RECOMMENDED MARKETS: (nearby mandis or eNAM)
6. ONE KEY TIP: (most important advice)

Be specific to Indian markets. Keep it brief."""

        try:
            nvidia_key = os.getenv('NVIDIA_API_KEY')
            response = req.post(
                'https://integrate.api.nvidia.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {nvidia_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'meta/llama-3.1-70b-instruct',
                    'messages': [
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ],
                    'max_tokens': 1024,
                    'temperature': 0.3
                },
                timeout=120
            )
            data = response.json()
            if 'choices' in data and len(data['choices']) > 0:
                result = data['choices'][0]['message']['content']
            else:
                result = 'ERROR: ' + str(data)

        except Exception as e:
            result = "ERROR: " + str(e)

    return render_template('market.html', result=result)

@app.route('/weather')
def weather():
    if 'user_id' not in session:
        return json.dumps({'error': 'Not logged in'})

    city = request.args.get('city', 'Pune')
    api_key = '2dec5cfda51538dd17fa2c2306c14969'

    try:
        weather_url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric'
        response = req.get(weather_url, timeout=10)
        data = response.json()

        if data.get('cod') == 200:
            weather_data = {
                'city': data['name'],
                'country': data['sys']['country'],
                'temp': round(data['main']['temp']),
                'feels_like': round(data['main']['feels_like']),
                'humidity': data['main']['humidity'],
                'wind_speed': round(data['wind']['speed'] * 3.6),
                'description': data['weather'][0]['description'].title(),
                'icon': data['weather'][0]['icon'],
                'min_temp': round(data['main']['temp_min']),
                'max_temp': round(data['main']['temp_max'])
            }
            return json.dumps({'success': True, 'data': weather_data})
        else:
            return json.dumps({'error': 'City not found'})

    except Exception as e:
        return json.dumps({'error': str(e)})

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=False)