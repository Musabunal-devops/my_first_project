
"""CV-related routes: index, upload, view, create profile."""
import os
from flask import Blueprint, current_app, flash, redirect, render_template, request, send_from_directory, url_for
from sqlalchemy.exc import IntegrityError
from database.models import CV, db
from fns.cv_extraction import extract_text_from_cv, extract_and_save_images_from_pdf
from fns.cv_parsing import parse_section_blocks, parse_cv_content, EXPECTED_HEADINGS
from fns.cv_contact import extract_contact_info
from fns.cv_name_utils import looks_like_name, clean_applicant_label, filter_name_blocks

# Helper function moved from helpers.py
def allowed_file(filename, allowed_extensions):
    """
    Check if a file's extension is in the list of allowed extensions.
    """
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in allowed_extensions
    )

cv_bp = Blueprint("cv", __name__)


@cv_bp.route("/")
def index():
    """Render the main homepage."""
    return render_template("index.html")


@cv_bp.route("/upload_cv_page")
def upload_cv_page():
    """Render the page for uploading a CV."""
    return render_template("upload_cv_page.html")


@cv_bp.route("/upload", methods=["POST"])
def upload_file():
    """Handle CV file upload."""
    if "file" not in request.files:
        flash("File not found.")
        return redirect(request.url)

    file = request.files["file"]

    if file.filename == "":
        flash("No file selected.")
        return redirect(request.url)

    if not allowed_file(file.filename, current_app.config["ALLOWED_EXTENSIONS"]):
        flash("Invalid file format.")
        return redirect(request.url)

    filename = file.filename
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
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

    if os.path.splitext(filename)[1].lower() == ".pdf":
        extracted_images = extract_and_save_images_from_pdf(
            filepath, current_app.config["UPLOAD_FOLDER"]
        )
        if extracted_images:
            photo_filename = os.path.basename(extracted_images[0])
        else:
            flash("Could not extract a profile photo from the CV.")

    flash("Your CV has been successfully uploaded!")

    return redirect(
        url_for("cv.create_profile_page", filename=filename, photo_filename=photo_filename)
    )


@cv_bp.route("/uploads/<filename>")
def uploaded_file_display(filename):
    """Serve the uploaded file from the UPLOAD_FOLDER."""
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@cv_bp.route("/view_cv/<filename>")
def view_uploaded_cv(filename):
    """Render the page that displays the uploaded CV and a button to create a profile."""
    return render_template("view_cv.html", filename=filename)


@cv_bp.route("/create_profile/<filename>")
def create_profile_page(filename):
    """Parse and render the profile creation page."""
    photo_filename = request.args.get("photo_filename")
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
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
