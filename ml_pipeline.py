import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import silhouette_score
import joblib
import os
import warnings
warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'Mall_Customers.csv')
MODEL_DIR = os.path.join(BASE_DIR, 'model')
os.makedirs(MODEL_DIR, exist_ok=True)

MODEL_PATH = os.path.join(MODEL_DIR, 'kmeans_model.pkl')
SCALER_PATH = os.path.join(MODEL_DIR, 'scaler.pkl')
ENCODER_PATH = os.path.join(MODEL_DIR, 'label_encoder.pkl')

def preprocess_data(df):
    if 'CustomerID' in df.columns:
        df = df.drop('CustomerID', axis=1)
    
    # Fill missing values
    df = df.fillna(df.mean(numeric_only=True))
    if 'Gender' in df.columns:
        df['Gender'] = df['Gender'].fillna(df['Gender'].mode()[0])
    
    # encode categorical
    le = LabelEncoder()
    df['Gender'] = le.fit_transform(df['Gender'])
    
    # scale numerical
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(df)
    
    return scaled_features, le, scaler, df

def train_and_evaluate():
    df = pd.read_csv(DATA_PATH)
    scaled_features, encoder, scaler, processed_df = preprocess_data(df)
    
    wcss = []
    silhouette_scores = []
    
    K_range = range(2, 11)
    for k in K_range:
        kmeans = KMeans(n_clusters=k, init='k-means++', n_init=10, random_state=42)
        kmeans.fit(scaled_features)
        wcss.append(float(kmeans.inertia_))
        score = silhouette_score(scaled_features, kmeans.labels_)
        silhouette_scores.append(float(score))
        
    optimal_k = K_range[np.argmax(silhouette_scores)]
    
    # Train final model
    final_kmeans = KMeans(n_clusters=optimal_k, init='k-means++', n_init=10, random_state=42)
    final_kmeans.fit(scaled_features)
    
    # Save models
    joblib.dump(final_kmeans, MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    joblib.dump(encoder, ENCODER_PATH)
    
    return {
        'optimal_k': int(optimal_k),
        'wcss': wcss,
        'silhouette_scores': silhouette_scores,
        'k_range': list(K_range),
        'max_silhouette': float(max(silhouette_scores))
    }

def get_cluster_label(cluster_id, centroids):
    labels = ["Standard Customer", "Target Customer", "Careful Customer", "Careless Customer", "Sensible Customer"]
    return labels[cluster_id % len(labels)]

_cached_kmeans = None
_cached_scaler = None
_cached_encoder = None

def get_models():
    global _cached_kmeans, _cached_scaler, _cached_encoder
    if not os.path.exists(MODEL_PATH):
        train_and_evaluate()
        
    if _cached_kmeans is None:
        _cached_kmeans = joblib.load(MODEL_PATH)
        _cached_scaler = joblib.load(SCALER_PATH)
        _cached_encoder = joblib.load(ENCODER_PATH)
        
    return _cached_kmeans, _cached_scaler, _cached_encoder

def predict_single(gender, age, income, spending):
    kmeans, scaler, encoder = get_models()
    
    g_encoded = encoder.transform([gender])[0]
    input_data = np.array([[g_encoded, age, income, spending]])
    scaled_input = scaler.transform(input_data)
    
    cluster = kmeans.predict(scaled_input)[0]
    centroids = kmeans.cluster_centers_
    
    inc_c = centroids[cluster][2]
    spd_c = centroids[cluster][3]
    
    if inc_c > 0.3 and spd_c > 0.3:
        label = "Target (High Income, High Spending)"
    elif inc_c > 0.3 and spd_c < -0.3:
        label = "Careful (High Income, Low Spending)"
    elif inc_c < -0.3 and spd_c > 0.3:
        label = "Careless (Low Income, High Spending)"
    elif inc_c < -0.3 and spd_c < -0.3:
        label = "Sensible (Low Income, Low Spending)"
    else:
        label = "Standard (Average Income and Spending)"
        
    return int(cluster), label

def get_dataset_insights():
    df = pd.read_csv(DATA_PATH)
    
    total_customers = len(df)
    avg_income = df['Annual Income (k$)'].mean()
    avg_age = df['Age'].mean()
    
    kmeans, _, _ = get_models()
    scaled_features, _, _, _ = preprocess_data(df)
    
    clusters = kmeans.predict(scaled_features)
    
    points = []
    for i, row in df.iterrows():
        points.append({
            'x': float(row['Annual Income (k$)']),
            'y': float(row['Spending Score (1-100)']),
            'cluster': int(clusters[i]),
            'gender': row['Gender'],
            'age': int(row['Age'])
        })
        
    return {
        'total_customers': int(total_customers),
        'avg_income': float(avg_income),
        'avg_age': float(avg_age),
        'scatter_points': points,
        'optimal_k': 10,
        'wcss': [29996.56, 26146.83, 22339.19, 19967.20, 17680.45, 15842.98, 14090.48, 12913.52, 11797.79],
        'silhouette_scores': [0.263, 0.224, 0.243, 0.238, 0.242, 0.256, 0.267, 0.268, 0.270],
        'k_range': [2, 3, 4, 5, 6, 7, 8, 9, 10]
    }
