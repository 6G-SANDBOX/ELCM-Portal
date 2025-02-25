from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, Optional, Length
from app.models import User
from flask_login import current_user


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    organization = StringField('Organization', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validateUsername(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validateEmail(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    rememberMe = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class ResetPasswordRequestForm(FlaskForm):
    """Form for users to request a password reset."""
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

class ResetPasswordForm(FlaskForm):
    """Form for users to reset their password."""
    password = PasswordField('New Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')

class UpdateProfileForm(FlaskForm):
    email = StringField('New Email', validators=[DataRequired(message="Email cannot be empty."), Email()])

    password = PasswordField('New Password', validators=[Optional(), Length(min=4, message="Password must be at least 6 characters.")])
    confirm_password = PasswordField('Confirm Password', validators=[Optional(), EqualTo('password', message="Passwords must match.")])

    current_password = PasswordField('Current Password', validators=[DataRequired(message="You must enter your current password.")])

    submit = SubmitField('Update')

    def validate_current_password(self, field):
        if not current_user.checkPassword(field.data):
            raise ValidationError("Incorrect current password.")