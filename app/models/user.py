import jwt
from typing import Dict, List, Set
from time import time
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login
from .experiment import Experiment
from datetime import datetime, timezone
from itsdangerous import URLSafeTimedSerializer

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    organization = db.Column(db.String(32))
    token = db.Column(db.String(512))
    tokenTimestamp = db.Column(db.DATETIME)
    is_approved = db.Column(db.Boolean, default=False)  # Admin approval required
    is_admin = db.Column(db.Boolean, default=False)  # Admin user flag
    experimentsRelation = db.relationship('Experiment', backref='author', lazy='dynamic')
    actionsRelation = db.relationship('Action', backref='author', lazy='dynamic')

    def __repr__(self):
        return f'<Id: {self.id}, Username: {self.username}, Email: {self.email}, Organization: {self.organization}>'

    def setPassword(self, password, issued_at=None):
        self.password_hash = generate_password_hash(password)
        if issued_at is not None:
            self.tokenTimestamp = datetime.fromtimestamp(issued_at)
        else:
            self.tokenTimestamp = datetime.now()


    def checkPassword(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def CurrentDispatcherToken(self):
        return self.token

    @property
    def Experiments(self) -> List:
        return Experiment.query.filter_by(user_id=self.id).order_by(Experiment.id.desc())

    @property
    def Actions(self) -> List:
        return Action.query.filter_by(user_id=self.id).order_by(Action.id.desc()).limit(10)

    def serialization(self) -> Dict[str, object]:
        experimentIds: List[int] = [exp.id for exp in self.Experiments]
        dictionary = {'Id': self.id, 'UserName': self.username, 'Email': self.email, 'Organization': self.organization,
                      'Experiments': experimentIds, 'IsApproved': self.is_approved, 'IsAdmin': self.is_admin}
        return dictionary

    def generate_reset_token(self):
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        data = {'email': self.email, 'issued_at': datetime.now(timezone.utc).timestamp()}
        return serializer.dumps(data, salt="password-reset")

    @staticmethod
    def verify_reset_token(token, expiration=600):
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = serializer.loads(token, salt="password-reset", max_age=expiration)
            email = data.get('email')
            issued_at = float(data.get('issued_at'))
        except Exception:
            return None, None

        user = User.query.filter_by(email=email).first()
        if user and user.tokenTimestamp and issued_at <= user.tokenTimestamp.timestamp():
            return None, None

        return user, issued_at

@login.user_loader
def load_user(id: int) -> User:
    return User.query.get(int(id))

class Action(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DATETIME)
    message = db.Column(db.String(256))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f'<Id: {self.id}, Timestamp: {self.timestamp}, Message: {self.message}, ' \
            f'User_id: {self.user_id}>'
