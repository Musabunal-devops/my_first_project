"""CV Profile Builder - Flask web application for uploading and parsing CVs."""
import os
import warnings
from dotenv import load_dotenv
from flask import Flask
from fns.extensions import db
from fns.models import User, CV, Feedback  # noqa: F401 — needed for db.create_all()
from fns.auth_routes import auth_bp
from fns.cv_routes import cv_bp
from fns.feedback_routes import feedback_bp

warnings.filterwarnings("ignore")

# --- ENVIRONMENT SETUP ---
load_dotenv()

# --- FLASK APP CONFIGURATION ---
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads/"
app.config["ALLOWED_EXTENSIONS"] = {"pdf", "doc", "docx"}
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

# --- INITIALIZE DATABASE ---
db.init_app(app)

# --- CREATE FOLDERS IF THEY DON'T EXIST ---
instance_path = os.path.join(app.root_path, "instance")
try:
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
except OSError:
    pass

if not os.path.exists(app.config["UPLOAD_FOLDER"]):
    os.makedirs(app.config["UPLOAD_FOLDER"])

# --- REGISTER BLUEPRINTS ---
app.register_blueprint(auth_bp)
app.register_blueprint(cv_bp)
app.register_blueprint(feedback_bp)

# --- Create Database Tables ---
with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
