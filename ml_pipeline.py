import pandas as pd
import numpy as np
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from functools import lru_cache
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.neighbors import KNeighborsClassifier
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

def get_model_paths(project_id=None, model_type='kmeans'):
    if project_id:
        mod_name = f'model_{model_type}_{project_id}.pkl'
        return (
            os.path.join(MODEL_DIR, mod_name),
            os.path.join(MODEL_DIR, f'scaler_{project_id}.pkl'),
            os.path.join(MODEL_DIR, f'label_encoder_{project_id}.pkl'),
            os.path.join(MODEL_DIR, f'knn_predictor_{model_type}_{project_id}.pkl')
        )
    return (
        os.path.join(MODEL_DIR, f'model_{model_type}_default.pkl'),
        os.path.join(MODEL_DIR, 'scaler_default.pkl'),
        os.path.join(MODEL_DIR, 'label_encoder_default.pkl'),
        os.path.join(MODEL_DIR, f'knn_predictor_{model_type}_default.pkl')
    )

def preprocess_data(df):
    if 'CustomerID' in df.columns:
        df = df.drop('CustomerID', axis=1)
    elif 'id' in df.columns.str.lower():
        id_col = df.columns[df.columns.str.lower() == 'id'][0]
        df = df.drop(id_col, axis=1)
    
    df = df.fillna(df.mean(numeric_only=True))
    
    cat_cols = df.select_dtypes(include=['object', 'category']).columns
    main_le = None
    
    for col in cat_cols:
        df[col] = df[col].fillna(df[col].mode()[0] if not df[col].mode().empty else 'Unknown')
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col])
        if col.lower() in ['gender', 'sex']:
            main_le = le
            
    if not main_le:
        main_le = LabelEncoder()
        main_le.fit(['Unknown'])
    
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(df)
    
    return scaled_features, main_le, scaler, df

def train_and_evaluate(data_path=DATA_PATH, project_id=None, model_type='kmeans'):
    df = pd.read_csv(data_path)
    scaled_features, encoder, scaler, processed_df = preprocess_data(df)
    
    wcss = []
    silhouette_scores = []
    max_k = min(11, len(df))
    K_range = range(2, max_k)
    optimal_k = 0
    
    if len(K_range) == 0:
        raise ValueError("Dataset too small for clustering")
        
    final_model = None
    knn_predictor = None
    labels = None
    
    if model_type == 'kmeans':
        for k in K_range:
            kmeans = KMeans(n_clusters=k, init='k-means++', n_init=10, random_state=42)
            kmeans.fit(scaled_features)
            wcss.append(float(kmeans.inertia_))
            silhouette_scores.append(float(silhouette_score(scaled_features, kmeans.labels_)))
            
        optimal_k = K_range[np.argmax(silhouette_scores)]
        final_model = KMeans(n_clusters=optimal_k, init='k-means++', n_init=10, random_state=42)
        final_model.fit(scaled_features)
        labels = final_model.labels_
        
    elif model_type == 'hierarchical':
        for k in K_range:
            hc = AgglomerativeClustering(n_clusters=k, linkage='ward')
            hc_labels = hc.fit_predict(scaled_features)
            silhouette_scores.append(float(silhouette_score(scaled_features, hc_labels)))
            
        optimal_k = K_range[np.argmax(silhouette_scores)]
        final_model = AgglomerativeClustering(n_clusters=optimal_k, linkage='ward')
        labels = final_model.fit_predict(scaled_features)
        
    elif model_type == 'dbscan':
        # Simple DBSCAN, using eps=0.5, min_samples=5 as default
        final_model = DBSCAN(eps=0.5, min_samples=5)
        labels = final_model.fit_predict(scaled_features)
        # Note: DBSCAN doesn't compute WCSS easily, so we leave it empty
        unique_labels = set(labels)
        if len(unique_labels) > 1: # Ignore if all noise
            silhouette_scores.append(float(silhouette_score(scaled_features, labels)))
        optimal_k = len(unique_labels) - (1 if -1 in labels else 0)

    # Train a KNN predictor for algorithms that don't support .predict() (or even for Kmeans for unified API)
    # We only fit the KNN on non-noise points
    valid_idx = labels != -1
    if sum(valid_idx) > 0:
        knn_predictor = KNeighborsClassifier(n_neighbors=3)
        knn_predictor.fit(scaled_features[valid_idx], labels[valid_idx])
    else:
        knn_predictor = None

    m_path, s_path, e_path, knn_path = get_model_paths(project_id, model_type)
    joblib.dump(final_model, m_path)
    joblib.dump(scaler, s_path)
    joblib.dump(encoder, e_path)
    if knn_predictor:
        joblib.dump(knn_predictor, knn_path)
    
    return {
        'optimal_k': int(optimal_k),
        'wcss': wcss,
        'silhouette_scores': silhouette_scores,
        'k_range': list(K_range),
        'max_silhouette': float(max(silhouette_scores)) if silhouette_scores else 0.0,
        'model_type': model_type
    }

def get_cluster_label(cluster_id):
    labels = ["Standard Segment", "Target Segment", "Careful Segment", "Careless Segment", "Sensible Segment"]
    return labels[cluster_id % len(labels)] if cluster_id >= 0 else "Outlier/Noise"

_cached_models = {}

def get_models(data_path=DATA_PATH, project_id=None, model_type='kmeans'):
    global _cached_models
    m_path, s_path, e_path, knn_path = get_model_paths(project_id, model_type)
    
    if not os.path.exists(m_path):
        train_and_evaluate(data_path, project_id, model_type)
        
    cache_key = f"{project_id}_{model_type}"
    if cache_key not in _cached_models:
        _cached_models[cache_key] = (
            joblib.load(m_path),
            joblib.load(s_path),
            joblib.load(e_path),
            joblib.load(knn_path) if os.path.exists(knn_path) else None
        )
    return _cached_models[cache_key]

def predict_single(gender, age, income, spending, project_id=None, data_path=DATA_PATH, model_type='kmeans'):
    model, scaler, encoder, knn_predictor = get_models(data_path, project_id, model_type)
    
    try:
        g_encoded = encoder.transform([gender])[0]
    except:
        g_encoded = 0
        
    input_data = np.array([[g_encoded, age, income, spending]])
    scaled_input = scaler.transform(input_data)
    
    if knn_predictor:
        cluster = knn_predictor.predict(scaled_input)[0]
    elif hasattr(model, 'predict'):
        cluster = model.predict(scaled_input)[0]
    else:
        cluster = -1 # fallback
        
    # Generalized labeling
    label = get_cluster_label(int(cluster))
    return int(cluster), label

@lru_cache(maxsize=32)
def get_dataset_insights(data_path=DATA_PATH, project_id=None, model_type='kmeans'):
    df = pd.read_csv(data_path)
    total_customers = len(df)
    
    income_col = next((c for c in df.columns if 'income' in c.lower()), None)
    age_col = next((c for c in df.columns if 'age' in c.lower()), None)
    spending_col = next((c for c in df.columns if 'score' in c.lower() or 'spending' in c.lower()), None)
    gender_col = next((c for c in df.columns if 'gender' in c.lower() or 'sex' in c.lower()), None)
    
    avg_income = df[income_col].mean() if income_col else 0
    avg_age = df[age_col].mean() if age_col else 0
    
    model, _, _, knn_predictor = get_models(data_path, project_id, model_type)
    scaled_features, _, _, _ = preprocess_data(df)
    
    if hasattr(model, 'labels_'):
        clusters = model.labels_
    elif knn_predictor:
        clusters = knn_predictor.predict(scaled_features)
    elif hasattr(model, 'predict'):
        clusters = model.predict(scaled_features)
    else:
        clusters = np.zeros(total_customers)
        
    points = []
    for i, row in df.iterrows():
        points.append({
            'x': float(row[income_col]) if income_col else 0,
            'y': float(row[spending_col]) if spending_col else 0,
            'cluster': int(clusters[i]),
            'gender': row[gender_col] if gender_col else 'Unknown',
            'age': float(row[age_col]) if age_col else 0
        })
        
    optimal_k = len(set(clusters)) - (1 if -1 in clusters else 0)
    
    return {
        'total_customers': int(total_customers),
        'avg_income': float(avg_income),
        'avg_age': float(avg_age),
        'scatter_points': points,
        'optimal_k': optimal_k,
        'features_used': list(df.columns),
        'model_type': model_type
    }

@lru_cache(maxsize=32)
def compute_elbow_method(data_path=DATA_PATH):
    df = pd.read_csv(data_path)
    scaled_features, _, _, _ = preprocess_data(df)
    
    k_range = list(range(1, 11))
    wcss = []
    
    if len(scaled_features) > 10:
        for k in k_range:
            kmeans = KMeans(n_clusters=k, init='k-means++', n_init=10, random_state=42)
            kmeans.fit(scaled_features)
            wcss.append(float(kmeans.inertia_))
    return {"k_range": k_range, "wcss": wcss}

@lru_cache(maxsize=32)
def compute_silhouette_scores(data_path=DATA_PATH):
    try:
        df = pd.read_csv(data_path)
        
        # Ensure: dataset is not empty
        if df.empty:
            return {"k_values": [], "scores": []}
            
        # Select features (income, spending score)
        income_col = next((c for c in df.columns if 'income' in c.lower()), None)
        spending_col = next((c for c in df.columns if 'score' in c.lower() or 'spending' in c.lower()), None)
        
        if income_col and spending_col:
            features = df[[income_col, spending_col]]
        else:
            features = df.select_dtypes(include=[np.number])
            
        # Ensure: no NaN values
        features = features.dropna()
        if features.empty or len(features) <= 10:
            return {"k_values": [], "scores": []}
            
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(features)
        
        k_values = list(range(2, 11))
        scores = []
        
        # Ensure: clusters > 1 (loop runs from 2 to 10)
        for k in k_values:
            model = KMeans(n_clusters=k, random_state=42)
            labels = model.fit_predict(scaled_features)
            score = silhouette_score(scaled_features, labels)
            scores.append(float(score))
            
        return {"k_values": k_values, "scores": scores}
            
    except Exception as e:
        print(f"Error computing silhouette scores: {e}")
        return {"k_values": [], "scores": []}
