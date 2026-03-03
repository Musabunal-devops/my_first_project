"""Authentication routes: register, login."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError
from fns.extensions import db
from fns.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register")
def register():
    """Render the user registration form page."""
    return render_template("register.html")


@auth_bp.route("/register_post", methods=["POST"])
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
        return redirect(url_for("auth.register"))

    # Check if email already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash("This email is already registered. Please use a different email address.")
        return redirect(url_for("auth.register"))

    new_user = User(first_name=first_name, last_name=last_name, email=email)
    new_user.set_password(password)

    try:
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! You can now log in.")
        return redirect(url_for("auth.login"))

    except IntegrityError:
        db.session.rollback()
        flash("This email is already registered. Please use a different email address.")
        return redirect(url_for("auth.register"))

    except (OSError, RuntimeError) as e:
        db.session.rollback()
        print(f"Error during registration: {e}")
        flash("An unexpected error occurred. Please try again.")
        return redirect(url_for("auth.register"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Render the login form page and handle login form submission."""

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            flash("Successfully logged in!")
            return redirect(url_for("cv.upload_cv_page"))
        else:
            flash("Email or password is incorrect. Please try again.")
            return redirect(url_for("auth.login"))

    return render_template("login.html")
