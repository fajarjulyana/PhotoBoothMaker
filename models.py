from datetime import datetime
from flask_login import UserMixin
from main import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    frames = db.relationship('Frame', backref='creator', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'

class Frame(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    file_path = db.Column(db.String(255), nullable=False)
    thumbnail_path = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    settings = db.Column(db.JSON, default={})
    
    def __repr__(self):
        return f'<Frame {self.name}>'

class PrintJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_path = db.Column(db.String(255), nullable=False)
    printer_name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), default='pending')  # pending, printing, completed, failed, canceled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    cups_job_id = db.Column(db.Integer)
    error_message = db.Column(db.Text)
    
    def __repr__(self):
        return f'<PrintJob {self.id} - {self.status}>'

class PhotoSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    photos = db.relationship('Photo', backref='session', lazy='dynamic')
    
    def __repr__(self):
        return f'<PhotoSession {self.session_id}>'

class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_path = db.Column(db.String(255), nullable=False)
    thumbnail_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    session_id = db.Column(db.Integer, db.ForeignKey('photo_session.id'))
    frame_id = db.Column(db.Integer, db.ForeignKey('frame.id'), nullable=True)
    frame = db.relationship('Frame')
    
    def __repr__(self):
        return f'<Photo {self.id} - {self.file_path}>'