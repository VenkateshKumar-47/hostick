import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = "hostick-super-secret-dev-key"
    COLLEGE_NAME = "Coimbatore Institute of Technology"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(BASE_DIR, 'hostick.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Photo upload settings for Food / Mess complaints
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads", "food_complaints")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB limit
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}