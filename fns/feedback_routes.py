"""Feedback API routes."""
from flask import Blueprint, request
from sqlalchemy.exc import IntegrityError
from database.models import db
from database.models import CV, Feedback

feedback_bp = Blueprint("feedback", __name__)


@feedback_bp.route("/api/feedback", methods=["POST"])
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

    cv = CV.query.filter_by(filename=data["cv_filename"]).first()
    if not cv:
        return {"success": False, "message": "CV not found"}, 404

    try:
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


@feedback_bp.route("/api/feedback/<filename>", methods=["GET"])
def get_feedback(filename):
    """API endpoint to get all approved feedback for a CV."""
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
