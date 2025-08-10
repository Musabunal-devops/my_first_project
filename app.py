from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

from dotenv import load_dotenv
# from flask_mail import Mail, Message # KALDIRILDI: Flask-Mail artık kullanılmıyor
load_dotenv()

app = Flask(__name__)
# --- Configuration ---
app.config['UPLOAD_FOLDER'] = 'uploads/'  # Folder where uploaded files will be saved
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'doc', 'docx'}  # Allowed file extensions
# PostgreSQL Database URI - Replace 'cv_app_user' and 'Musab1zehra.' with your actual credentials
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # To suppress a warning
# SECRET_KEY is essential for security. CHANGE THIS TO A LONG, RANDOM STRING!
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# KALDIRILDI: Flask-Mail Configuration bloğu
# app.config['MAIL_SERVER'] = 'smtp.gmail.com'
# app.config['MAIL_PORT'] = 587
# app.config['MAIL_USE_TLS'] = True
# app.config['MAIL_USE_SSL'] = False
# app.config['MAIL_USERNAME'] = 'senin_eposta_adresin@gmail.com'
# app.config['MAIL_PASSWORD'] = 'senin_eposta_sifren_veya_uygulama_sifren'
# app.config['MAIL_DEFAULT_SENDER'] = 'senin_eposta_adresin@gmail.com'


# --- Initialize Database ---
db = SQLAlchemy(app) # Initialize SQLAlchemy with your Flask app
# mail = Mail(app)     # KALDIRILDI: Flask-Mail nesnesinin başlatılması

# --- Create 'uploads' folder if it doesn't exist ---
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# --- Database Model Definition ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(512), nullable=False)
    last_name = db.Column(db.String(512), nullable=False)
    email = db.Column(db.String(512), unique=True, nullable=False) # unique=True'yu geri almadık, çünkü önceki talebiniz buydu.
    password_hash = db.Column(db.String(512), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'

# --- Create Database Tables (Run only once or when models change) ---
with app.app_context():
    db.create_all()

# --- Helper Function ---
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_cv_page')
def upload_cv_page():
    return render_template('upload_cv.html')

@app.route('/upload', methods=['POST'])
def upload_file():
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
    return render_template('register.html')

@app.route('/register_post', methods=['POST'])
def register_post():
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    email = request.form['email']
    password = request.form['password']
    confirm_password = request.form['confirm_password']

    # --- Validation and Database Logic ---
    if password != confirm_password:
        flash('Passwords do not match! Please try again.')
        return redirect(url_for('register'))

    # Daha önce aynı e-posta ile kayıt olma opsiyonunu açmak için yorum satırı yaptığımız kısım:
    # existing_user = User.query.filter_by(email=email).first()
    # if existing_user:
    #    flash('An account with this email already exists. Please use a different email or log in.')
    #    return redirect(url_for('register'))

    new_user = User(first_name=first_name, last_name=last_name, email=email)
    new_user.set_password(password)

    try:
        db.session.add(new_user)
        db.session.commit()

        # KALDIRILDI: E-posta gönderme kodu bloğu
        # import threading
        # threading.Thread(target=mail.send, args=[msg]).start()

        # Kayıt başarılı olduğunda kullanıcıyı başarı sayfasına yönlendir.
        return redirect(url_for('registration_success'))

    except Exception as e:
        db.session.rollback()
        print(f"Error during registration: {e}")
        flash('An error occurred during registration. Please try again.')
        return redirect(url_for('register'))

# --- Yeni Rota: Başarılı Kayıt Sayfası ---
@app.route('/registration_success')
def registration_success():
    """Displays a success page after user registration."""
    return render_template('registration_success.html')

if __name__ == '__main__':
    app.run(debug=True)