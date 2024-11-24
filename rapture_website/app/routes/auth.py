from flask import render_template, request, redirect, url_for, flash, session, Blueprint
from app.services.auth import bcrypt, auth_required
from app.models import User, Experiment
from app.services.db import user_collection
import time
import os

# Create a Blueprint for auth-related routes
bp = Blueprint('auth', __name__)

@bp.route('/account', methods=['GET'])
@auth_required
def account(user: User):
    return render_template("account.html", user=user,
                           exps=Experiment.get_mul_by_id(user.experiment_ids))


@bp.route('/learn', methods=['GET'])
def learn():
    if 'loggedin' in session and 'name_id' in session:
        return render_template('learn.html')  # Assuming you have a template for the /learn page
    else:
        return redirect(url_for('auth.login'))


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'loggedin' in session or 'name_id' in session:
        return redirect(url_for('auth.account'))

    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        user = user_collection.find_one({"name_id": request.form['username']})
        if user and bcrypt.check_password_hash(user['password'], request.form["password"]):
            session['loggedin'] = True
            session['name_id'] = user['name_id']
            if user.get('admin', False):
                session['admin'] = True
            next_page = session.pop('next', url_for('auth.account'))
            return redirect(next_page)
        else:
            flash('Error: Invalid username or password')

    return render_template('login.html')


@bp.route('/create_account', methods=['GET', 'POST'])
def create_account():
    if 'loggedin' in session or 'name_id' in session:
        return redirect(url_for('auth.account'))

    if request.method == 'POST':
        name_id = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not name_id or not email or not password:
            flash("Error: All fields are required.")
            return render_template('create_account.html')

        if user_collection.find_one({"email": email}):
            flash(f"Error: Email '{email}' already exists.")
            return render_template('create_account.html')

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = {
            "name_id": name_id,
            "email": email,
            "password": hashed_password,
            "experiment_ids": [],
            "admin": False,
            "created_at": time.time()
        }

        try:
            user_collection.insert_one(new_user)
        except Exception as e:
            flash(f"Error: Could not create account. {e}")
            return render_template('create_account.html')

        session['loggedin'] = True
        session['name_id'] = name_id

        flash("Success: Account created successfully.")
        return redirect(url_for('auth.account'))

    return render_template('create_account.html')


@bp.route('/profile', methods=['GET'])
@auth_required
def profile(user: User):
    return render_template("account.html", user=user)


@bp.route('/update_profile', methods=['POST'])
@auth_required
def update_profile(user: User):
    name_id = session['name_id']
    existing_user = user_collection.find_one({"name_id": name_id})

    if not existing_user:
        flash("Error: User not found.")
        return redirect(url_for('auth.account'))

    update_data = {}

    # Check and update username
    new_name = request.form.get('name')
    if new_name and new_name != existing_user.get('name_id'):
        update_data['name_id'] = new_name
        session['name_id'] = new_name  # Update session

    # Check and update email
    new_email = request.form.get('email')
    if new_email and new_email != existing_user.get('email'):
        if user_collection.find_one({"email": new_email}):
            flash("Error: Email is already in use.")
            return redirect(url_for('auth.account'))
        update_data['email'] = new_email

    # Check and update password
    new_password = request.form.get('password')
    if new_password:
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        update_data['password'] = hashed_password

    # Handle profile picture upload
    if 'profile_pic' in request.files:
        profile_pic = request.files['profile_pic']
        if profile_pic.filename:
            file_path = os.path.join('static/uploads', profile_pic.filename)
            profile_pic.save(file_path)
            update_data['profile_pic'] = file_path

    if update_data:
        try:
            user_collection.update_one({"name_id": name_id}, {"$set": update_data})
            flash("Profile updated successfully.")
        except Exception as e:
            flash(f"Error: Could not update profile. {e}")
    else:
        flash("No changes were made to your profile.")

    return redirect(url_for('auth.profile'))


@bp.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('next', None)
    session.pop('name_id', None)
    session.pop('admin', None)
    return redirect(url_for('main.index'))
