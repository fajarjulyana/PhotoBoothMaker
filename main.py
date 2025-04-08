import os
import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create database model base class
class Base(DeclarativeBase):
    pass

# Initialize SQLAlchemy with the model
db = SQLAlchemy(model_class=Base)

# Initialize LoginManager
login_manager = LoginManager()
login_manager.login_view = 'login'

# Create the Flask application
app = Flask(__name__)

# Load configuration
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "a-very-secure-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///photobooth.db"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Set up directories for file uploads
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['FRAMES_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'frames')
app.config['PHOTOS_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'photos')

# Ensure directories exist
os.makedirs(app.config['FRAMES_FOLDER'], exist_ok=True)
os.makedirs(app.config['PHOTOS_FOLDER'], exist_ok=True)

# Initialize extensions with app
db.init_app(app)
login_manager.init_app(app)

# Import the models to register them with SQLAlchemy
from models import User, Frame, PrintJob, PhotoSession, Photo

# Create all tables
with app.app_context():
    db.create_all()

# Import routes after app initialization
import routes

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)