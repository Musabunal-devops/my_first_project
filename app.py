"""CV Profile Builder - Flask web application for uploading and parsing CVs."""
# --- IMPORTS ---
import os
import warnings
from datetime import datetime
from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash
from cv_parser import (
    parse_section_blocks,
    parse_cv_content,
    extract_text_from_cv,
    extract_and_save_images_from_pdf,
    extract_contact_info,
    looks_like_name,
    clean_applicant_label,
    filter_name_blocks,
    EXPECTED_HEADINGS,
)

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
db = SQLAlchemy(app)

# --- CREATE FOLDERS IF THEY DON'T EXIST ---
# Ensure the instance folder exists for the SQLite database
instance_path = os.path.join(app.root_path, "instance")
try:
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
except OSError:
    pass

if not os.path.exists(app.config["UPLOAD_FOLDER"]):
    os.makedirs(app.config["UPLOAD_FOLDER"])



class User(db.Model):
    """Database model representing application users."""

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(512), nullable=False)
    last_name = db.Column(db.String(512), nullable=False)
    email = db.Column(db.String(512), unique=True, nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    def set_password(self, password):
        """Hash and store the provided password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify a plaintext password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email}>"

    cvs = db.relationship("CV", backref="user", lazy=True)


# --- CV Model Definition ---
class CV(db.Model):
    """
    CV model for storing uploaded CV file paths and related info.

    Attributes
    ----------
    id : int
        The primary key for the CV.
    user_id : int
        Foreign key to the User who uploaded the CV (optional).
    filename : str
        The name of the uploaded file.
    filepath : str
        The path to the uploaded file on the server.
    upload_time : datetime
        The time the CV was uploaded.
    """

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    filename = db.Column(db.String(512), nullable=False)
    filepath = db.Column(db.String(1024), nullable=False)
    upload_time = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f"<CV {self.filename} by user {self.user_id}>"

    feedbacks = db.relationship(
        "Feedback", backref="cv", lazy=True, cascade="all, delete-orphan"
    )


class Feedback(db.Model):
    """
    Feedback model for storing user feedback on CVs.

    Attributes
    ----------
    id : int
        The primary key for the feedback.
    cv_id : int
        Foreign key to the CV this feedback is for.
    user_id : int
        Foreign key to the User who gave the feedback (optional for anonymous).
    author_name : str
        Name of the person giving feedback (for display).
    content : str
        The actual feedback text.
    rating : int
        Optional rating from 1-5 stars.
    feedback_type : str
        Type of feedback (general, design, content, etc.).
    is_anonymous : bool
        Whether the feedback should be displayed anonymously.
    created_at : datetime
        When the feedback was created.
    is_approved : bool
        Whether the feedback has been approved by moderators.
    """

    id = db.Column(db.Integer, primary_key=True)
    cv_id = db.Column(db.Integer, db.ForeignKey("cv.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    author_name = db.Column(db.String(255), nullable=False, default="Anonymous User")
    content = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=True)  # 1-5 stars
    feedback_type = db.Column(
        db.String(50), default="general"
    )  # general, design, content, skills, etc.
    is_anonymous = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    is_approved = db.Column(db.Boolean, default=True)  # Auto-approve for now

    def __repr__(self):
        return f"<Feedback for CV {self.cv_id} by {self.author_name}>"


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
    return render_template("upload_cv_page.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    """Handle CV file upload."""
    if "file" not in request.files:
        flash("File not found.")
        return redirect(request.url)

    file = request.files["file"]

    # If the filename is empty (no file was selected)
    if file.filename == "":
        flash("No file selected.")
        return redirect(request.url)

    # Check if the file's extension is allowed
    if not allowed_file(file.filename):
        flash("Invalid file format.")
        return redirect(request.url)

    # Proceed if the file is safe and valid
    filename = file.filename
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    # --- Save CV info to database ---
    try:
        new_cv = CV(filename=filename, filepath=filepath)
        db.session.add(new_cv)
        db.session.commit()
    except (IntegrityError, OSError) as e:
        db.session.rollback()
        flash(f"Could not save CV to database: {e}")

    extracted_images = []
    photo_filename = None

    # Perform image extraction only for PDFs
    if os.path.splitext(filename)[1].lower() == ".pdf":
        extracted_images = extract_and_save_images_from_pdf(
            filepath, app.config["UPLOAD_FOLDER"]
        )
        # If an image was found, use the first one
        if extracted_images:
            photo_filename = os.path.basename(extracted_images[0])
        else:
            flash("Could not extract a profile photo from the CV.")

    flash("Your CV has been successfully uploaded!")

    return redirect(
        url_for("create_profile_page", filename=filename, photo_filename=photo_filename)
    )


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

    # Check if email already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash("This email is already registered. Please use a different email address.")
        return redirect(url_for("register"))

    new_user = User(first_name=first_name, last_name=last_name, email=email)
    new_user.set_password(password)

    try:
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! You can now log in.")
        return redirect(url_for("login"))

    except IntegrityError:
        # Caught when a user tries to register with a pre-existing email.
        db.session.rollback()
        flash("This email is already registered. Please use a different email address.")
        return redirect(url_for("register"))

    except (OSError, RuntimeError) as e:
        db.session.rollback()
        print(f"Error during registration: {e}")
        flash("An unexpected error occurred. Please try again.")
        return redirect(url_for("register"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Render the login form page and handle login form submission."""

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # Look for the user in the database by their email address
        user = User.query.filter_by(email=email).first()

        # If a user is found and the password is correct
        if user and user.check_password(password):
            flash("Successfully logged in!")
            return redirect(url_for("upload_cv_page"))
        else:
            flash("Email or password is incorrect. Please try again.")
            return redirect(url_for("login"))

    # When a GET request is received, show the login form
    return render_template("login.html")


# A new route to serve the uploaded CV file to the browser
@app.route("/uploads/<filename>")
def uploaded_file_display(filename):
    """
    Serve the uploaded file from the UPLOAD_FOLDER.
    """
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# A new page to show the uploaded CV and a button to create a profile
@app.route("/view_cv/<filename>")
def view_uploaded_cv(filename):
    """
    Render the page that displays the uploaded CV and a button to create a profile.
    """
    return render_template("view_cv.html", filename=filename)


@app.route("/create_profile/<filename>")
def create_profile_page(filename):
    """Parse and render the profile creation page."""
    photo_filename = request.args.get("photo_filename")
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    cv_text = extract_text_from_cv(filepath)
    print("DEBUG cv_text:", cv_text)
    parsed_sections = {}
    section_blocks = {}
    contact_info = {}
    display_labels = {}
    if cv_text:
        contact_info = extract_contact_info(cv_text)
        print("DEBUG contact_info:", contact_info)
        parsed_sections = parse_cv_content(cv_text)
        print("DEBUG parsed_sections:", parsed_sections)
        for section, text in parsed_sections.items():
            section_blocks[section] = parse_section_blocks(text, section)

        display_labels = {}
        applicant_name = None
        name_blocks = None

        for section in list(section_blocks.keys()):
            if section not in EXPECTED_HEADINGS.values() and looks_like_name(section):
                if applicant_name is None:
                    applicant_name = clean_applicant_label(section)
                    raw_blocks = section_blocks.pop(section)
                    name_blocks = filter_name_blocks(raw_blocks)
                    break

        if applicant_name:
            if "PROFIL" in section_blocks:
                if name_blocks:
                    section_blocks["PROFIL"].extend(name_blocks)
                display_labels["PROFIL"] = applicant_name
            else:
                section_blocks[applicant_name] = name_blocks if name_blocks else []
                display_labels[applicant_name] = applicant_name

        for section in section_blocks:
            if section not in display_labels:
                display_labels[section] = section

        profile_section_key = None
        if applicant_name:
            if "PROFIL" in section_blocks:
                profile_section_key = "PROFIL"
            elif applicant_name in section_blocks:
                profile_section_key = applicant_name
        elif "PROFIL" in section_blocks:
            # Even without applicant_name, put PROFIL first
            profile_section_key = "PROFIL"

        if profile_section_key:
            ordered_keys = [profile_section_key]
            ordered_keys.extend(
                k for k in section_blocks if k != profile_section_key
            )
            original_blocks = section_blocks
            section_blocks = {k: original_blocks[k] for k in ordered_keys}
            display_labels = {k: display_labels.get(k, k) for k in ordered_keys}

        print("DEBUG section_blocks:", section_blocks)
    return render_template(
        "create_profile.html",
        sections=parsed_sections,
        section_blocks=section_blocks,
        display_labels=display_labels,
        filename=filename,
        photo_filename=photo_filename,
        contact_info=contact_info,
    )


@app.route("/api/feedback", methods=["POST"])
def submit_feedback():
    """
    API endpoint to submit feedback for a CV.

    Expected JSON payload:
    {
        "cv_filename": "example.pdf",
        "content": "This is great feedback!",
        "author_name": "John Doe",
        "rating": 5,
        "feedback_type": "general",
        "is_anonymous": true
    }
    """
    data = request.get_json()

    if not data or not data.get("content") or not data.get("cv_filename"):
        return {"success": False, "message": "Missing required fields"}, 400

    # Find the CV by filename
    cv = CV.query.filter_by(filename=data["cv_filename"]).first()
    if not cv:
        return {"success": False, "message": "CV not found"}, 404

    try:
        # Create new feedback
        feedback = Feedback(
            cv_id=cv.id,
            content=data["content"],
            author_name=data.get("author_name", "Anonymous User"),
            rating=data.get("rating"),
            feedback_type=data.get("feedback_type", "general"),
            is_anonymous=data.get("is_anonymous", True),
        )

        db.session.add(feedback)
        db.session.commit()

        return {
            "success": True,
            "message": "Feedback submitted successfully",
            "feedback": {
                "id": feedback.id,
                "author_name": feedback.author_name,
                "content": feedback.content,
                "rating": feedback.rating,
                "created_at": feedback.created_at.strftime("%d.%m.%Y %H:%M"),
                "feedback_type": feedback.feedback_type,
            },
        }
    except (IntegrityError, OSError) as e:
        db.session.rollback()
        return {"success": False, "message": f"Error saving feedback: {str(e)}"}, 500


@app.route("/api/feedback/<filename>", methods=["GET"])
def get_feedback(filename):
    """
    API endpoint to get all approved feedback for a CV.
    """
    cv = CV.query.filter_by(filename=filename).first()
    if not cv:
        return {"success": False, "message": "CV not found"}, 404

    feedbacks = (
        Feedback.query.filter_by(cv_id=cv.id, is_approved=True)
        .order_by(Feedback.created_at.desc())
        .all()
    )

    feedback_list = []
    for feedback in feedbacks:
        feedback_list.append(
            {
                "id": feedback.id,
                "author_name": feedback.author_name,
                "content": feedback.content,
                "rating": feedback.rating,
                "feedback_type": feedback.feedback_type,
                "created_at": feedback.created_at.strftime("%d.%m.%Y %H:%M"),
                "is_anonymous": feedback.is_anonymous,
            }
        )

    return {"success": True, "feedbacks": feedback_list, "count": len(feedback_list)}


if __name__ == "__main__":
    app.run(debug=True)
