import os
import sys
from werkzeug.security import generate_password_hash
from main import app, db
from models import User

def create_admin_user(username, email, password):
    """Create an admin user if it doesn't exist"""
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Check if an admin user already exists
        admin_user = User.query.filter_by(is_admin=True).first()
        if admin_user:
            print(f"Admin user already exists: {admin_user.username}")
            return
        
        # Create the admin user
        password_hash = generate_password_hash(password)
        admin = User(
            username=username,
            email=email,
            password_hash=password_hash,
            is_admin=True
        )
        
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user created: {username}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python setup.py <username> <email> <password>")
        sys.exit(1)
    
    username = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]
    
    create_admin_user(username, email, password)