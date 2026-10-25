"""Application factory and local development entry point."""
import os
from pathlib import Path
from flask import Flask, jsonify, send_from_directory
from .extensions import db
from . import models  # Register ORM tables before create_all().
from .database import init_db
from .routes import api

BASE_DIR=Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR/".env")
except ImportError:
    pass


def create_app(test_config=None):
    app=Flask(__name__,static_folder="../frontend",static_url_path="")
    database_file=Path(os.getenv("DATABASE_PATH",str(BASE_DIR/"instance"/"fitness.db"))).resolve()
    app.config.from_mapping(SECRET_KEY=os.getenv("SECRET_KEY","dev-only-change-this-secret"),
        SQLALCHEMY_DATABASE_URI="sqlite:///"+database_file.as_posix(), SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"connect_args":{"check_same_thread":False}}, DATABASE_FILE=str(database_file),
        LEGACY_DATABASE=str(BASE_DIR/"instance"/"coach.sqlite3"), SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE","false").lower()=="true",MAX_CONTENT_LENGTH=1_000_000)
    if test_config:
        app.config.update(test_config)
        if "DATABASE" in test_config and "SQLALCHEMY_DATABASE_URI" not in test_config:
            database_file=Path(test_config["DATABASE"]).resolve()
            app.config["DATABASE_FILE"]=str(database_file)
            app.config["SQLALCHEMY_DATABASE_URI"]="sqlite:///"+database_file.as_posix()
            if "LEGACY_DATABASE" not in test_config: app.config["LEGACY_DATABASE"]=None
    Path(app.config["DATABASE_FILE"]).parent.mkdir(parents=True,exist_ok=True)
    db.init_app(app);app.register_blueprint(api);init_db(app)
    @app.get("/")
    def index():return send_from_directory(app.static_folder,"index.html")
    @app.get("/<path:path>")
    def static_files(path):
        if path.startswith("api/"):return jsonify(error="Not found."),404
        return send_from_directory(app.static_folder,path)
    @app.errorhandler(413)
    def too_large(_):return jsonify(error="Request is too large."),413
    return app


if __name__=="__main__":create_app().run(host="0.0.0.0",port=int(os.getenv("PORT","5000")),debug=os.getenv("FLASK_DEBUG","false").lower()=="true")
