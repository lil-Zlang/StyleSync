"""
Style Weaver Flask Application Package

This package contains the core logic for the Style Weaver MVP application.
"""

from flask import Flask
from dotenv import load_dotenv
import os

def create_app():
    """
    Application factory pattern for Flask app creation.
    
    Returns:
        Flask: Configured Flask application instance
    """
    # Load environment variables
    load_dotenv()
    
    # Create Flask app instance
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
    # Basic configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # Register routes
    from app.routes import main
    app.register_blueprint(main)
    
    return app
