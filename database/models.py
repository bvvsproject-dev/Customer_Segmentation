from database.db import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Relationships
    projects = db.relationship('Project', backref='owner', lazy=True)
    history = db.relationship('PredictionHistory', backref='user', lazy=True)

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PredictionHistory(db.Model):
    __tablename__ = 'prediction_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    gender = db.Column(db.String(10))
    age = db.Column(db.Float)
    income = db.Column(db.Float)
    spending = db.Column(db.Float)
    cluster = db.Column(db.Integer)
    label = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
