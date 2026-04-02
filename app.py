from flask import Flask, jsonify, request, render_template, session, redirect, url_for, g, send_file
import os
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import google.generativeai as genai
from ml_pipeline import train_and_evaluate, predict_single, get_dataset_insights, MODEL_PATH, compute_elbow_method, compute_silhouette_scores, get_cluster_label, DATA_PATH
from database.db import db
from database.models import User, Project, PredictionHistory
from werkzeug.utils import secure_filename
from core.insights import explain_segment, suggest_strategy
from core.simulation import run_business_simulation
from core.pdf_generator import create_pdf_report
import io
from datetime import timedelta

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GEMINI_API_KEY_HERE":
    genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__)
app.secret_key = 'super_secret_segment_key_2026'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    db.create_all()

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
        
        try:
            new_user = User(username=username, email=email, password_hash=generate_password_hash(password))
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('login'))
        except Exception:
            db.session.rollback()
            error = "Username or Email already exists"
    return render_template('register.html', error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter((User.username == username) | (User.email == username)).first()
        
        if user is None or not check_password_hash(user.password_hash, password):
            error = "Invalid username or password"
        else:
            session.clear()
            session['user_id'] = user.id
            session['username'] = user.username
            if request.form.get('remember_me'):
                session.permanent = True
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

@app.route('/api/upload', methods=['POST'])
@login_required
def upload_data():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400
    
    file = request.files['file']
    project_name = request.form.get('project_name', 'Unnamed Project')
    
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
        
    if file and file.filename.endswith('.csv'):
        filename = secure_filename(file.filename)
        unique_filename = f"{session['user_id']}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # Save to Project DB
        new_project = Project(user_id=session['user_id'], name=project_name, file_path=file_path)
        db.session.add(new_project)
        db.session.commit()
        
        return jsonify({"status": "success", "message": "File uploaded successfully", "project_id": new_project.id}), 200
        
    return jsonify({"status": "error", "message": "Invalid file format. Only CSV allowed."}), 400

@app.route('/api/train', methods=['POST'])
@login_required
def train_api():
    try:
        data = request.json or {}
        project_id = data.get('project_id')
        model_type = data.get('model_type', 'kmeans')
        
        data_path = None
        if project_id:
            project = Project.query.get(project_id)
            if project and project.user_id == session.get('user_id'):
                data_path = project.file_path
                
        if data_path:
            result = train_and_evaluate(data_path, project_id, model_type)
        else:
            result = train_and_evaluate(model_type=model_type)
            
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

def get_advanced_recommendation(label, gender, age, income, spending):
    try:
        from dotenv import load_dotenv
        import os
        load_dotenv(override=True)
        current_api_key = os.getenv("GEMINI_API_KEY")
        if not current_api_key or current_api_key == "YOUR_GEMINI_API_KEY_HERE":
            raise Exception("No Gemini API key")

        genai.configure(api_key=current_api_key)
        
        # Enforcing JSON format at the API level
        model = genai.GenerativeModel('gemini-2.5-flash', generation_config={"response_mime_type": "application/json"})
        prompt = f"""
        You are a top-tier business strategist. 
        A customer (Gender: {gender}, Age: {age}, Income: {income}k, Spending Score: {spending}) belongs to the segment '{label}'.
        
        Return ONLY valid JSON with this exact structure:
        {{
            "html_strategy": "<b>Key Characteristic:</b> ... <br> <b>Product Focus:</b> ... <br> <b>Engagement:</b> ...",
            "channels": [
                {{
                    "type": "whatsapp",
                    "title": "WhatsApp Message",
                    "discount": "15% OFF",
                    "pitch": "Hey! We noticed you love premium items. Here is 15% off..."
                }},
                {{
                    "type": "ads",
                    "title": "Social Ad",
                    "discount": "Free Shipping",
                    "pitch": "Stop waiting. Get free shipping on your next order today!"
                }},
                {{
                    "type": "email",
                    "title": "Email Newsletter",
                    "discount": "BOGO Deal",
                    "pitch": "Exclusive VIP Deal just for you..."
                }}
            ]
        }}
        """
        response = model.generate_content(prompt)
        import json
        return json.loads(response.text)
    except Exception as e:
        import traceback
        traceback.print_exc()
        rec_text = get_recommendation(label)
        return {
            "html_strategy": f"<b>Key Characteristic:</b> Follows '{label}' trends.<br><b>Product Focus:</b> Selected catalog items.<br><b>Engagement:</b> {rec_text}",
            "channels": [
                {
                    "type": "whatsapp",
                    "title": "WhatsApp Message",
                    "discount": "10% OFF",
                    "pitch": f"Hey! We have an exclusive offer just for you. {rec_text}"
                },
                {
                    "type": "ads",
                    "title": "Social Ad",
                    "discount": "Free Shipping",
                    "pitch": f"Don't miss out on curated items perfectly suited for you. Shop now!"
                },
                {
                    "type": "email",
                    "title": "Email Newsletter",
                    "discount": "BOGO Deal",
                    "pitch": "Hi there, take a look at our latest VIP deals..."
                }
            ]
        }

@app.route('/api/predict', methods=['POST'])
@login_required
def predict_api():
    try:
        data = request.json
        gender = data.get('gender')
        age = float(data.get('age'))
        income = float(data.get('income'))
        spending = float(data.get('spending'))
        project_id = data.get('project_id')
        model_type = data.get('model_type', 'kmeans')
        
        data_path = None
        if project_id:
            project = Project.query.get(project_id)
            if project and project.user_id == session.get('user_id'):
                data_path = project.file_path
        
        if data_path:
            cluster, label = predict_single(gender, age, income, spending, project_id, data_path, model_type)
        else:
            cluster, label = predict_single(gender, age, income, spending, model_type=model_type)
            
        # Log to History
        history = PredictionHistory(
            user_id=session['user_id'],
            gender=gender,
            age=age,
            income=income,
            spending=spending,
            cluster=cluster,
            label=label
        )
        db.session.add(history)
        db.session.commit()
        
        advanced_data = get_advanced_recommendation(label, gender, age, income, spending)
        
        return jsonify({
            "status": "success",
            "cluster": cluster,
            "label": label,
            "recommendation": advanced_data.get("html_strategy", get_recommendation(label)),
            "channels": advanced_data.get("channels", [])
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

def get_path_for_project(project_id):
    if project_id and project_id != 'null':
        p = Project.query.get(project_id)
        if p: return os.path.join(app.config['UPLOAD_FOLDER'], p.filename)
    return DATA_PATH

@app.route('/api/elbow-data', methods=['GET'])
@login_required
def elbow_api():
    project_id = session.get('project_id') if hasattr(session, 'get') else None
    data_path = get_path_for_project(project_id)
    try:
        data = compute_elbow_method(data_path)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/silhouette-data', methods=['GET'])
@login_required
def silhouette_api():
    project_id = session.get('project_id') if hasattr(session, 'get') else None
    data_path = get_path_for_project(project_id)
    try:
        data = compute_silhouette_scores(data_path)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/data', methods=['GET'])
@login_required
def data_api():
    try:
        project_id = request.args.get('project_id')
        model_type = request.args.get('model_type', 'kmeans')
        
        data_path = None
        if project_id:
            project = Project.query.get(project_id)
            if project and project.user_id == session.get('user_id'):
                data_path = project.file_path
                
        if data_path:
            insights = get_dataset_insights(data_path, project_id, model_type)
        else:
            insights = get_dataset_insights(model_type=model_type) # Default dataset
            
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

@app.route('/api/explain', methods=['POST'])
@login_required
def explain_api():
    try:
        data = request.json
        label = data.get('label')
        cluster_stats = data.get('cluster_stats', 'No stats provided')
        
        explanation = explain_segment(label, cluster_stats)
        strategy = suggest_strategy(label, cluster_stats)
        
        return jsonify({
            "status": "success",
            "explanation": explanation,
            "strategy": strategy
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/simulate', methods=['POST'])
@login_required
def simulate_api():
    try:
        data = request.json
        label = data.get('label', 'Standard')
        action = data.get('action')
        revenue = float(data.get('current_revenue', 10000))
        
        result = run_business_simulation(label, action, revenue)
        return jsonify({
            "status": "success",
            "simulation": result
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/export/pdf', methods=['POST'])
@login_required
def export_pdf_api():
    try:
        data = request.json
        project_id = session.get('project_id') 
        data_path = get_path_for_project(project_id)
        model_type = data.get('model_type', 'kmeans')
        
        insights_data = get_dataset_insights(data_path, project_id, model_type)
        all_points = insights_data.get('scatter_points', [])
        
        clusters_map = {}
        for pt in all_points:
            cid = int(pt['cluster'])
            if cid not in clusters_map:
                clusters_map[cid] = {'points': [], 'label': get_cluster_label(cid)}
            clusters_map[cid]['points'].append(pt)
            
        final_clusters = {}
        for cid, cdata in clusters_map.items():
            pts = cdata['points']
            final_clusters[cid] = {
                'label': cdata['label'],
                'size': len(pts),
                'avg_age': sum(p['age'] for p in pts) / len(pts) if pts else 0,
                'avg_income': sum(p['x'] for p in pts) / len(pts) if pts else 0,
                'avg_score': sum(p['y'] for p in pts) / len(pts) if pts else 0,
                'points': pts[:30]
            }
            
        data['stats']['cluster_count'] = len(final_clusters)
        data['clusters'] = final_clusters
        
        pdf_buffer = create_pdf_report(data)
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name='Advanced_Cluster_Report.pdf',
            mimetype='application/pdf'
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
