from typing import Optional
from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_user, logout_user, login_required
from urllib.parse import urlparse
from app import db
from app.models import User
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm, ResetPasswordRequestForm, ResetPasswordForm, UpdateProfileForm
from Helper import Config, Log
from app.email import send_email
from itsdangerous import URLSafeTimedSerializer
from flask import current_app

config = Config()
branding = config.Branding

def generate_reset_token(user):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(
        [user.email, user.password_hash],  
        salt="password-reset"
    )


def verify_reset_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email, password_hash = serializer.loads(token, salt="password-reset", max_age=expiration)
    except:
        return None

    user = User.query.filter_by(email=email).first()
    
    if user and user.password_hash == password_hash:
        return email

    return None  

# ==========================
# User Registration
# ==========================
@bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handles user registration. First user becomes admin automatically."""
    
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if the username or email already exists
        def _exist():
            if User.query.filter_by(username=form.username.data).first() is not None:
                form.username.errors.append("Username already registered")
                return True
            elif User.query.filter_by(email=form.email.data).first() is not None:
                form.email.errors.append("Email already registered")
                return True
            return False

        if _exist():
            return render_template(
                'auth/register.html',
                favicon=branding.FavIcon,
                title='Register',
                platformName=branding.Platform,
                header=branding.Header,
                form=form,
                description=config.Branding.Description,
                ewEnabled=config.EastWest.Enabled,
                logo=branding.Logo
            )

        user: Optional[User] = None
        try:
            is_first_user = User.query.count() == 0  # Check if this is the first user
            user = User(username=form.username.data, email=form.email.data, organization=form.organization.data)
            user.setPassword(form.password.data)
            user.is_approved = True if is_first_user else False  # Auto-approve first user
            user.is_admin = True if is_first_user else False  # First user is an admin
            db.session.add(user)
            db.session.commit()

            if not is_first_user:
                flash("Your account is pending approval by an administrator.", 'warning')

            return redirect(url_for('auth.login'))
        except Exception as e:
            Log.E(f"Exception while creating new user: {e}")
            Log.D(f"User: {user}")
            flash(f"Unable to create user", 'error')

    return render_template(
        'auth/register.html',
        favicon=branding.FavIcon,
        title='Register',
        platformName=branding.Platform,
        header=branding.Header,
        logo=branding.Logo,
        form=form,
        description=config.Branding.Description
    )

# ==========================
# User Login
# ==========================
@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handles user login, checking if the user is approved before granting access."""
    
    if current_user.is_authenticated:
        Log.I(f'The user is already authenticated')
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user: User = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.checkPassword(form.password.data):
            Log.I(f'Invalid username or password')
            flash('Invalid username or password', 'error')
            return redirect(url_for('auth.login'))

        if not user.is_approved:
            flash('Your account has not yet been approved by an administrator.', 'warning')
            return redirect(url_for('auth.login'))

        login_user(user, remember=form.rememberMe.data)
        Log.I(f'User {user.username} logged in')

        nextPage = request.args.get('next')
        if not nextPage or urlparse(nextPage).netloc != '':
            nextPage = url_for('main.index')

        return redirect(nextPage)

    return render_template(
        'auth/login.html',
        title='Sign In',
        favicon=branding.FavIcon,
        logo=branding.Logo,
        platformName=branding.Platform,
        header=branding.Header,
        form=form,
        description=branding.Description
    )

# ==========================
# User Logout
# ==========================
@bp.route('/logout')
def logout():
    """Handles user logout."""
    
    logout_user()
    Log.I(f'User logged out')
    return redirect(url_for('main.index'))



# ==========================
# Approving a User
# ==========================
@bp.route('/admin/approve_user/<int:user_id>', methods=['POST'])
@login_required
def approve_user(user_id):
    """Allows an admin to approve a user, granting them access to the system."""
    
    if not current_user.is_admin:
        flash('You do not have permission to do this.', 'danger')
        return redirect(url_for('main.index'))

    user = User.query.get(user_id)
    if user:
        user.is_approved = True
        db.session.commit()

    return redirect(url_for('auth.manage_users'))

# ==========================
# Rejecting a User (Deleting User)
# ==========================
@bp.route('/admin/reject_user/<int:user_id>', methods=['POST'])
@login_required
def reject_user(user_id):
    """Allows an admin to reject a user, permanently removing them."""
    
    if not current_user.is_admin:
        flash('You do not have permission to do this.', 'danger')
        return redirect(url_for('main.index'))

    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()

    return redirect(url_for('auth.manage_users'))

@bp.route('/admin/manage_users')
@login_required
def manage_users():
    """Displays a list of all users for the admin to manage."""
    
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.index'))

    users = User.query.all()  # Get all users
    
    return render_template(
        'admin/manage_users.html',
        users=users,
        favicon=branding.FavIcon,
        platformName=branding.Platform,
        header=branding.Header
    )


@bp.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    """Allows an admin to delete a user."""
    
    if not current_user.is_admin:
        flash('You do not have permission to do this.', 'danger')
        return redirect(url_for('main.index'))

    user = User.query.get(user_id)
    
    if user:
        if user.is_admin:
            flash('You cannot delete an admin user.', 'danger')
            return redirect(url_for('auth.manage_users'))
        
        db.session.delete(user)
        db.session.commit()

    return redirect(url_for('auth.manage_users'))
# ==========================
# Reset Password Request
# ==========================
@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    """Handles password reset requests."""

    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = ResetPasswordRequestForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user:
            token = generate_reset_token(user)
            send_email(
                subject="Reset Your Password",
                recipient=user.email,  
                template='email/reset_password',  
                token=token,
                user=user
            )

        flash('Check your email for the instructions to reset your password.', 'info')
        return redirect(url_for('auth.login'))

    return render_template(
        'auth/reset_password_request.html',
        favicon=branding.FavIcon,
        logo=branding.Logo,
        platformName=branding.Platform,
        header=branding.Header,
        form=form,
        description=branding.Description
    )

# ==========================
# Reset Password
# ==========================
@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):

    email = verify_reset_token(token)
    if not email:
        flash('Invalid or expired token.', 'danger')
        return redirect(url_for('auth.reset_password_request'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('auth.reset_password_request'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.setPassword(form.password.data)
        db.session.commit()
        flash('Your password has been reset!', 'success')
        return redirect(url_for('auth.login'))

    return render_template(
        'auth/reset_password.html',
        favicon=branding.FavIcon,
        logo=branding.Logo,
        platformName=branding.Platform,
        header=branding.Header,
        form=form,
        description=branding.Description
    )

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = UpdateProfileForm()
    updated = False

    if form.validate_on_submit():
        if not current_user.checkPassword(form.current_password.data):
            flash('Incorrect current password. Changes were not saved.', 'danger')
        else:
            if form.email.data and form.email.data != current_user.email:
                current_user.email = form.email.data
                updated = True
            
            if form.password.data:
                current_user.setPassword(form.password.data)
                updated = True

            if updated:
                db.session.commit()
                flash('Your profile has been updated. Please log in again.', 'warning')
                logout_user()  
                return redirect(url_for('auth.login'))  
            else:
                flash('No changes were made.', 'info')

    form.email.data = current_user.email
    return render_template(
        'auth/profile.html', 
        form=form, 
        favicon=branding.FavIcon,
        platformName=branding.Platform, 
        header=branding.Header)

@bp.route('/delete_account', methods=['POST'])
@login_required
def delete_account():

    if current_user.is_admin:
        flash("Admin accounts cannot be deleted!", "danger")
        return redirect(url_for('auth.profile'))

    user = User.query.get(current_user.id)  

    logout_user()  

    db.session.delete(user)  
    db.session.commit()

    flash('Your account has been deleted permanently.', 'danger')
    return redirect(url_for('main.index'))
