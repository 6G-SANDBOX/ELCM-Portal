from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_moment import Moment
from config import Config
from Helper import Log, Facility, Config as AppConfig


db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
login.login_message = 'Please log in to access this page.'
bootstrap = Bootstrap()
mail = Mail()
moment = Moment()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
    app_config = AppConfig()
    email_api = app_config.EmailApi

    app.config.update(
        MAIL_SERVER=email_api.Server,
        MAIL_PORT=email_api.Port,
        MAIL_USERNAME=email_api.User,
        MAIL_PASSWORD=email_api.Password,
        MAIL_USE_TLS=email_api.TLS,
        MAIL_USE_SSL=email_api.SSL
    )

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    bootstrap.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    Log.Initialize(app)

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    from app.experiment import bp as experiment_bp
    app.register_blueprint(experiment_bp, url_prefix='/experiment')

    from app.execution import bp as execution_bp
    app.register_blueprint(execution_bp, url_prefix='/execution')

    Log.I("Requesting facility information to ELCM...")
    Facility.Reload()

    eastWest = AppConfig().EastWest
    if eastWest.Enabled:
        from app.east_west import bp as eastWest_bp
        app.register_blueprint(eastWest_bp, url_prefix='/distributed')
    Log.I(f'Optional East/West interface is {Log.State(eastWest.Enabled)}')

    Log.I('5Genesis startup')
    return app


from app import models
