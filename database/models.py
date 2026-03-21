"""Database models for the CV Profile Builder application."""
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from flask_sqlalchemy import SQLAlchemy

# Shared Flask extension
db = SQLAlchemy()


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
