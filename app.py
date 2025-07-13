from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)

# --- Configuration ---
app.config['UPLOAD_FOLDER'] = 'uploads/'  # Folder where uploaded files will be saved
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'doc', 'docx'}  # Allowed file extensions
# PostgreSQL Database URI - Replace 'cv_app_user' and 'Musab1zehra.' with your actual credentials
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://cv_app_user:Musab1zehra.@localhost:5432/cv_app_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # To suppress a warning
# SECRET_KEY is essential for security. CHANGE THIS TO A LONG, RANDOM STRING!
app.config['SECRET_KEY'] = 'your_secret_key_here_change_this_to_a_long_random_string'

# --- Initialize Database ---
db = SQLAlchemy(app) # Initialize SQLAlchemy with your Flask app

# --- Create 'uploads' folder if it doesn't exist ---
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# --- Database Model Definition ---
# This class defines the 'user' table in your PostgreSQL database
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(512), nullable=False)
    last_name = db.Column(db.String(512), nullable=False)
    email = db.Column(db.String(512), unique=True, nullable=False)
    password_hash = db.Column(db.String(512), nullable=False) # Stores the hashed password

    def set_password(self, password):
        """Hashes the given password and stores it."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Checks if the given password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'

# --- Create Database Tables (Run only once or when models change) ---
# This ensures tables are created when the app starts if they don't exist.
# In a production environment, consider using Flask-Migrate for migrations.
with app.app_context():
    db.create_all()

# --- Helper Function ---
def allowed_file(filename):
    """Checks if the file extension is in the allowed list."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# --- Routes ---

@app.route('/')
def index():
    """Home page - Shows welcome message, login, and registration options."""
    return render_template('index.html')

@app.route('/upload_cv_page')
def upload_cv_page():
    return render_template('upload_cv.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles the CV upload process."""
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    file = request.files['file']

    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = file.filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        flash("Your CV has been successfully uploaded! More features are coming soon.")
        return redirect(url_for('index'))
    else:
        flash("Invalid file format. Please upload a file in PDF, DOC, or DOCX format.")
        return redirect(request.url)

@app.route('/register')
def register():
    """Displays the user registration form."""
    return render_template('register.html')

@app.route('/register_post', methods=['POST'])
def register_post():
    """Receives and processes data from the registration form."""
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    email = request.form['email']
    password = request.form['password']
    confirm_password = request.form['confirm_password'] # Assuming your register.html has a confirm_password field

    # --- Validation and Database Logic ---
    if password != confirm_password:
        flash('Passwords do not match! Please try again.')
        return redirect(url_for('register'))

    # Check if a user with this email already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash('An account with this email already exists. Please use a different email or log in.')
        return redirect(url_for('register'))

    # Create a new user instance
    new_user = User(first_name=first_name, last_name=last_name, email=email)
    new_user.set_password(password) # Hash and store the password

    try:
        db.session.add(new_user) # Add the new user to the session
        db.session.commit() # Commit changes to the database
        flash('Account created successfully! You can now log in.')
        return redirect(url_for('index'))
    except Exception as e:
        db.session.rollback() # Rollback on error
        print(f"Error during registration: {e}") # Log error for debugging
        flash('An error occurred during registration. Please try again.')
        return redirect(url_for('register'))

if __name__ == '__main__':
    app.run(debug=True)