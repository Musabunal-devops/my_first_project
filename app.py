"""This is the main application file for the CV-app."""

import os
import re
import pdfplumber
import docx
import fitz #PyMuPDF
from PIL import Image
import io

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for, send_from_directory
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


def extract_text_from_cv(filepath):
    """
    Extracts text from the specified file path.
    """
    try:
        file_ext = os.path.splitext(filepath)[1].lower()
        text = ""
        if file_ext == ".pdf":
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
        elif file_ext in [".doc", ".docx"]:
            doc = docx.Document(filepath)
            for para in doc.paragraphs:
                text += para.text + "\n"
        return text
    except Exception as e:
        print(f"Text extraction error: {e}")
        return None

def extract_and_save_images_from_pdf(filepath, output_folder):
    """
    Extracts and saves images from the specified PDF file.
    """
    found_images = []
    try:
        doc = fitz.open(filepath)
        for i in range(len(doc)):
            images = doc.get_page_images(i)
            if not images:
                continue

            for img_index, img in enumerate(images):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_data = base_image["image"]
                
                # Skip if image data is missing or too small
                if not image_data or len(image_data) < 100:
                    continue

                # Create a unique filename
                filename = os.path.basename(filepath)
                # We can set a threshold to prevent confusion with small images.
                # Typically, profile photos are larger than a certain pixel size.
                try:
                    img_stream = io.BytesIO(image_data)
                    pil_img = Image.open(img_stream)
                    # We can check the image size, for example, if it's larger than 100x100.
                    if pil_img.width > 100 and pil_img.height > 100:
                        image_filename = f"{os.path.splitext(filename)[0]}_profile_photo.png"
                        image_path = os.path.join(output_folder, image_filename)
                        
                        with open(image_path, "wb") as f:
                            f.write(image_data)
                        
                        found_images.append(image_filename)
                        # We try to find the most relevant one by returning only the first suitable photo.
                        return [image_filename] # Return only one image

                except Exception as e:
                    print(f"Image size check error: {e}")
                    continue

    except Exception as e:
        print(f"Error extracting image from PDF: {e}")
    
    # If this point is reached, no image was found.
    print("A profile photo could not be extracted from the CV.")
    return found_images

def parse_cv_content(text):
    """
    Parses CV text by dynamically identifying potential section headings.
    Headings are assumed to be a line consisting of all uppercase letters.
    """
    sections = {}
    lines = text.split('\n')
    current_section = "Other"
    
    # Initialize a key for the "Other" section
    sections[current_section] = ""

    for line in lines:
        stripped_line = line.strip()
        # Check if the line is a potential heading: all uppercase, not too short, and not empty.
        if stripped_line and stripped_line.isupper() and len(stripped_line.split()) <= 4 and len(stripped_line) > 2:
            current_section = stripped_line
            sections[current_section] = ""
        elif stripped_line:
            sections[current_section] += stripped_line + '\n'

    # Clean up empty sections and organize the "Other" section if it exists.
    cleaned_sections = {k: v.strip() for k, v in sections.items() if v.strip()}
    
    # If no headings are found, assign all text to the "Other" section
    if not cleaned_sections and text.strip():
        return {"Other": text.strip()}
    
    return cleaned_sections



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
    # Check if a file named 'file' exists in the request
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
    
    extracted_images = []
    photo_filename = None
    
    # Perform image extraction only for PDFs
    if os.path.splitext(filename)[1].lower() == ".pdf":
        extracted_images = extract_and_save_images_from_pdf(filepath, app.config["UPLOAD_FOLDER"])
        
        # If an image was found, use the first one
        if extracted_images:
            photo_filename = os.path.basename(extracted_images[0])
        else:
            flash("Could not extract a profile photo from the CV.")

    flash("Your CV has been successfully uploaded!")
    
    return redirect(url_for("create_profile_page", 
                            filename=filename, 
                            photo_filename=photo_filename))
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

        # Look for the user in the database by their email address
        user = User.query.filter_by(email=email).first()

        # If a user is found and the password is correct
        if user and user.check_password(password):
            flash("Logged in successfully!")
            return redirect(url_for("upload_cv_page"))
        else:
            flash("Invalid email or password. Please try again.")
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


# Placeholder route for redirecting to the profile creation page
# The create_profile_page route in app.py (unchanged but as a reminder)
@app.route("/create_profile/<filename>")
def create_profile_page(filename):
    photo_filename = request.args.get('photo_filename') # photo_filename is retrieved from here
    
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    cv_text = extract_text_from_cv(filepath)
    parsed_sections = {}
    if cv_text:
        parsed_sections = parse_cv_content(cv_text)
    
    return render_template("create_profile.html", 
                           sections=parsed_sections, 
                           filename=filename,
                           photo_filename=photo_filename) # It's sent to the template from here
if __name__ == "__main__":
    app.run(debug=True)