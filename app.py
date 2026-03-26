from flask import Flask, jsonify, request, render_template, session, redirect, url_for, g
import os
import sqlite3
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import google.generativeai as genai
from ml_pipeline import train_and_evaluate, predict_single, get_dataset_insights, MODEL_PATH

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
    genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__)
app.secret_key = 'super_secret_segment_key_2026'

DATABASE = 'users.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')
        db.commit()

init_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_user():
    return dict(user_id=session.get('user_id'), username=session.get('username'))

# Auto-train on startup if model doesn't exist
if not os.path.exists(MODEL_PATH):
    print("Model not found. Auto-training now...")
    try:
        train_and_evaluate()
        print("Auto-training completed successfully.")
    except Exception as e:
        print(f"Error during auto-training: {e}")

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        db = get_db()
        try:
            db.execute('INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                       (username, email, generate_password_hash(password)))
            db.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            error = "Username or Email already exists"
    return render_template('register.html', error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ? OR email = ?', (username, username)).fetchone()
        
        if user is None or not check_password_hash(user['password_hash'], password):
            error = "Invalid username or password"
        else:
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('index'))
            
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/predict_page')
@login_required
def predict_page():
    return render_template('predict.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/api/train', methods=['POST'])
def train_api():
    try:
        result = train_and_evaluate()
        return jsonify({"status": "success", "data": result}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def get_recommendation(label):
    if "Target" in label:
        return "Promote premium products, exclusive offers, and loyalty programs."
    elif "Careful" in label:
        return "Offer discounts on essentials, emphasize value and quality."
    elif "Careless" in label:
        return "Promote trendy and impulse-buy products with clear payment options."
    elif "Sensible" in label:
        return "Focus on affordability, bulk discounts, and necessities."
    else:
        return "Provide standard marketing campaigns and seasonal promotions."

@app.route('/api/predict', methods=['POST'])
def predict_api():
    try:
        data = request.json
        gender = data.get('gender')
        age = float(data.get('age'))
        income = float(data.get('income'))
        spending = float(data.get('spending'))
        
        cluster, label = predict_single(gender, age, income, spending)
        
        return jsonify({
            "status": "success",
            "cluster": cluster,
            "label": label,
            "recommendation": get_recommendation(label)
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route('/api/data', methods=['GET'])
def data_api():
    try:
        insights = get_dataset_insights()
        # Removed train_and_evaluate() here to prevent OOM memory spikes on Render free tier
        return jsonify({"status": "success", "data": insights}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat_api():
    try:
        # Reload dotenv on every request just in case it was updated
        from dotenv import load_dotenv
        load_dotenv(override=True)
        current_api_key = os.getenv("GEMINI_API_KEY")

        data = request.json
        user_message = data.get('message')
        
        if not current_api_key or current_api_key == "YOUR_GEMINI_API_KEY_HERE":
            return jsonify({"status": "error", "message": "Gemini API key not configured. Please add it to the .env file."}), 400
            
        genai.configure(api_key=current_api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(
            f"You are a helpful AI assistant for a Customer Segmentation Web App. "
            f"Please keep your answers concise. Always format with basic HTML like <br>, <b>, <i> only (NO markdown asterisks like * or **). "
            f"User question: {user_message}"
        )
        
        return jsonify({
            "status": "success",
            "reply": response.text
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
