from typing import Optional
from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_user, logout_user, login_required
from urllib.parse import urlparse
from app import db
from app.models import User
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm, ResetPasswordRequestForm, ResetPasswordForm
from Helper import Config, Log

config = Config()
branding = config.Branding

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
                logo=branding.Logo if hasattr(branding, "Logo") else "default_logo.png"
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
            flash(f"User '{user.username}' created", 'info')

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
        logo=branding.Logo if hasattr(branding, "Logo") else "default_logo.png",
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
        logo=branding.Logo if hasattr(branding, "Logo") else "default_logo.png",
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
# Admin Panel for Approving Users
# ==========================
@bp.route('/admin/approve_users')
@login_required
def approve_users():
    """Displays a list of users pending approval for admins."""
    
    if not current_user.is_admin:
        flash('You do not have permission to access this page.', 'danger')
        return redirect(url_for('main.index'))

    users = User.query.filter_by(is_approved=False).all()
    
    return render_template(
        'admin/approve_users.html',
        users=users,
        favicon="favicon.ico",
        platformName="MyPlatform",
        header=branding.Header
    )

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
        flash(f'User {user.username} successfully approved.', 'success')

    return redirect(url_for('auth.approve_users'))

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
        flash(f'User {user.username} has been rejected.', 'danger')

    return redirect(url_for('auth.approve_users'))

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
        favicon="favicon.ico",
        platformName="MyPlatform",
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
        flash(f'User {user.username} has been deleted.', 'danger')

    return redirect(url_for('auth.manage_users'))
