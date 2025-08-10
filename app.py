"""This is the main application file for the CV-app."""

import os

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

app = Flask(__name__)
# --- Configuration ---
app.config["UPLOAD_FOLDER"] = "uploads/"
app.config["ALLOWED_EXTENSIONS"] = {"pdf", "doc", "docx"}
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

# --- Initialize Database ---
db = SQLAlchemy(app)

# --- Create 'uploads' folder if it doesn't exist ---
if not os.path.exists(app.config["UPLOAD_FOLDER"]):
    os.makedirs(app.config["UPLOAD_FOLDER"])


# --- Database Model Definition ---
class User(db.Model):
    """
    User model for the database, representing registered users.

    Attributes
    ----------
    id : int
        The primary key for the user.
    first_name : str
        The user's first name.
    last_name : str
        The user's last name.
    email : str
        The user's unique email address.
    password_hash : str
        The hashed password for the user.
    """

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(512), nullable=False)
    last_name = db.Column(db.String(512), nullable=False)
    email = db.Column(db.String(512), unique=True, nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)

    def set_password(self, password):
        """
        Hashe the provided password and sets it to the password_hash attribute.

        Parameters
        ----------
        password : str
            The plaintext password to be hashed.
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """
        Check if the provided password matches the stored hashed password.

        Parameters
        ----------
        password : str
            The plaintext password to be checked.

        Returns
        -------
        bool
            Returns True if the passwords match, False otherwise.
        """
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        """Return a string representation of the user."""
        return f"<User {self.email}>"


# --- Create Database Tables (Run only once or when models change) ---
with app.app_context():
    db.create_all()


# --- Helper Function ---
def allowed_file(filename):
    """
    Check if a file's extension is in the list of allowed extensions.

    Parameters
    ----------
    filename : str
        The name of the file to check.

    Returns
    -------
    bool
        Returns True if the file extension is allowed, False otherwise.
    """
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]
    )


# --- Routes ---


@app.route("/")
def index():
    """Render the main homepage."""
    return render_template("index.html")


@app.route("/upload_cv_page")
def upload_cv_page():
    """Render the page for uploading a CV."""
    return render_template("upload_cv.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    """
    Handle the file upload logic for CVs.

    Parameters
    ----------
    None
        This function receives file data from a POST request.

    Returns
    -------
    Response
        Redirects to the index page on success, or to the upload page on failure.
    """
    if "file" not in request.files:
        flash("No file part")
        return redirect(request.url)

    file = request.files["file"]

    if file.filename == "":
        flash("No selected file")
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = file.filename
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        flash("Your CV has been successfully uploaded! More features are coming soon.")
        return redirect(url_for("index"))
    else:
        flash("Invalid file format. Please upload a file in PDF, DOC, or DOCX format.")
        return redirect(request.url)


@app.route("/register")
def register():
    """Render the user registration form page."""
    return render_template("register.html")


@app.route("/register_post", methods=["POST"])
def register_post():
    """
    Handle user registration form submission.

    Parameters
    ----------
    None
        This function receives form data from a POST request.

    Returns
    -------
    Response
        Redirects to success or failure pages with a message.
    """
    first_name = request.form["first_name"]
    last_name = request.form["last_name"]
    email = request.form["email"]
    password = request.form["password"]
    confirm_password = request.form["confirm_password"]

    if password != confirm_password:
        flash("Passwords do not match! Please try again.")
        return redirect(url_for("register"))

    new_user = User(first_name=first_name, last_name=last_name, email=email)
    new_user.set_password(password)

    try:
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("registration_success"))

    except IntegrityError:
        # Caught when a user tries to register with a pre-existing email.
        db.session.rollback()
        flash("This email address is already registered. Please use a different one.")
        return redirect(url_for("register"))

    except Exception as e:
        # This is a general fallback for any other unexpected errors.
        db.session.rollback()
        print(f"Error during registration: {e}")
        flash("An unexpected error occurred. Please try again.")
        return redirect(url_for("register"))


@app.route("/registration_success")
def registration_success():
    """Display a success page after user registration."""
    return render_template("registration_success.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Render the login form page and handle login form submission."""
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            flash("Logged in successfully!")
            return redirect(url_for("index"))
        else:
            flash("Invalid email or password. Please try again.")
            return redirect(url_for("login"))
    
    # GET isteği geldiğinde, login formunu göster
    return render_template("login.html")

# Eski login_post rotasını silebilirsiniz, artık ihtiyacınız yok.


if __name__ == "__main__":
    app.run(debug=True)
