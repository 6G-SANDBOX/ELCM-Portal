import os
from dotenv import load_dotenv

load_dotenv(dotenv_path='./.flaskenv', verbose=True)
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = os.getenv('SECRET_KEY') or '__REPLACEWITHSECRETKEY__'
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL') or 'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = os.getenv('MAIL_SERVER') or 'localhost'
    MAIL_PORT = int(os.getenv('MAIL_PORT') or 8025)
    UPLOAD_FOLDER = 'uploads'
