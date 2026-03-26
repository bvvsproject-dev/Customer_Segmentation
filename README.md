# Mall Customer Segmentation using K-Means Clustering

A complete production-ready project featuring a Flask backend, K-Means clustering machine learning model, and a beautiful Neo UI glassmorphism frontend.

## Instructions to run in VS Code

1. Open this complete project folder (`customer segmentation (antigravity)`) in VS Code.
2. Open a new VS Code terminal (`Ctrl` + ` `` `).
3. Ensure you have Python installed. You may want to create a virtual environment first:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
4. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Run the backend application:
   ```bash
   python app.py
   ```
6. The model will automatically train itself upon the first run using the dataset in `data/Mall_Customers.csv`. Once you see `* Running on http://127.0.0.1:5000` in the terminal, open your browser and go to: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

## Features
- Complete K-Means auto-training (determines number of clusters automatically via Silhouette score).
- Live visualization of the Clustering plot, WCSS Elbow Method, and Silhouette scores using Chart.js on the dashboard.
- Stunning "Neo UI" layout using vanilla HTML/CSS.
