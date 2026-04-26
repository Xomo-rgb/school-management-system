import os
from flask import Flask, redirect, url_for
from config import Config
from routes.auth import auth_bp
from routes.student import student_bp
from routes.teacher import teacher_bp
from routes.admin import admin_bp
from routes.user import user_bp
from routes.assignment import assignment_bp
from routes.profile import profile_bp
from routes.temp_dashboard import temp_dashboard_bp
from firebase_db import close_db
from whitenoise import WhiteNoise


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STATIC_DIR = os.path.join(BASE_DIR, 'static')


def create_app():
    app = Flask(__name__)
    app.secret_key = Config.SECRET_KEY
    app.debug = Config.DEBUG

    app.teardown_appcontext(close_db)

    # all blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp, url_prefix='/students')
    app.register_blueprint(teacher_bp, url_prefix='/teachers')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(user_bp, url_prefix='/users')
    app.register_blueprint(assignment_bp, url_prefix='/assignments')
    app.register_blueprint(profile_bp, url_prefix='/profile')
    app.register_blueprint(temp_dashboard_bp)

    # Default route
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    return app

app = create_app()

app.wsgi_app = WhiteNoise(app.wsgi_app, root=STATIC_DIR)


if __name__ == "__main__":
    app.run()