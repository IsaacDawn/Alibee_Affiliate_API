# production_app.py - Temporary file for Render.com compatibility
# This file redirects to the actual backend app

import sys
import os

# Add backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Import the actual app
from backend.app import app

# Export the app for uvicorn
__all__ = ['app']
