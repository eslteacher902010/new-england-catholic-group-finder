# shell_helper.py
from main import app, db

with app.app_context():
    # Your custom DB code
    db.create_all()
