from flask import Flask, redirect, url_for, session, render_template
from config import Config
from models import db, Student, Admin, Notification


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    # Register Blueprints
    from routes.auth import auth_bp
    from routes.student import student_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp, url_prefix="/student")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.context_processor
    def inject_user_context():
        role = session.get("role")
        user_id = session.get("user_id")
        current_user = None
        unread_count = 0

        if role == "student" and user_id:
            current_user = db.session.get(Student, user_id)
            if current_user:
                unread_count = Notification.query.filter_by(
                    student_id=current_user.id, is_read=False
                ).count()
        elif role == "admin" and user_id:
            current_user = db.session.get(Admin, user_id)

        return dict(
            current_user=current_user,
            user_role=role,
            unread_count=unread_count,
            college_name=app.config["COLLEGE_NAME"],
        )

    @app.route("/")
    def index():
        role = session.get("role")
        if role == "student":
            return redirect(url_for("student.dashboard"))
        if role == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("auth.login"))

    @app.errorhandler(404)
    def not_found_error(error):
        return (
            "<h3>404 - Page Not Found</h3><p><a href='/'>Return to Hostick Home</a></p>",
            404,
        )

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return (
            "<h3>500 - Internal Server Error</h3><p>Please check your database connection and try again.</p>",
            500,
        )

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)