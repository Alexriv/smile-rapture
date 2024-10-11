from flask import render_template, request, redirect, url_for, flash, session, Blueprint

from app.services.auth import bcrypt, auth_required
from app.models import User, Experiment
from app.services.db import user_collection

# Create a Blueprint for auth-related routes
bp = Blueprint('auth', __name__)

@bp.route('/account', methods=['GET'])
@auth_required
def account(user: User):
    return render_template("account.html", user=user,
                           exps=Experiment.get_mul_by_id(user.experiment_ids))


@bp.route('/learn', methods=['GET'])
def learn():
    # Check if the user is logged in
    if 'loggedin' in session and 'name_id' in session:
        # If the user is logged in, redirect them to the /learn page
        return render_template('learn.html')  # Assuming you have a template for the /learn page
    else:
        # If the user is not logged in, redirect them to the login page
        return redirect(url_for('auth.login'))



@bp.route('/login', methods=['GET', 'POST'])
def login():
    # Check if user is already logged in
    if 'loggedin' in session or 'name_id' in session:
        return redirect(url_for('auth.account'))

    # Check if "username" and "password" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        # Attempt to find the user in the database
        user = User.get_by_id(str(request.form['username']))

        # If account exists and password is correct
        if user and bcrypt.check_password_hash(user.password, str(request.form["password"])):
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['name_id'] = user.name_id

            if user.name_id == 'admin':
                session['admin'] = True

            # session['email'] = user.email

            # Redirect to the page the user originally requested or to the account page
            next_page = session.pop('next', url_for('auth.account'))  # Use 'account' as the default
            return redirect(next_page)

        else:
            # Invalid login attempt
            flash('Error: Invalid username or password')

    # Show the login form with message (if any)
    return render_template('login.html')

@bp.route('/create_account', methods=['GET', 'POST'])
def create_account():
    # Check if user is already logged in
    if 'loggedin' in session or 'name_id' in session:
        return redirect(url_for('auth.account'))

    # Check if "username" and "password" POST requests exist (user submitted form)
    if (request.method == 'POST' and 'username' in request.form
            and 'email' in request.form and 'password' in request.form):
        name_id = str(request.form['username'])
        email = str(request.form['email'])

        # Check if username exists
        if not User.get_by_id(name_id):
            # Hash the password with bcrypt
            hashed_password = str(bcrypt.generate_password_hash(str(request.form['password'])).decode('utf-8'))

            # Create user object and push to DB
            user_collection.insert_one(User(name_id=name_id, email=email,
                                            password=hashed_password).json())

            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['name_id'] = name_id
            # session['email'] = email

            # Redirect to the page the user originally requested or to the account page
            flash(f"Success: Account created successfully")
            return redirect(session.pop('next', url_for('auth.account')))

        else:
            # Invalid login attempt
            flash(f"Error: Account with username '{name_id}' already exists")

    # Show the creation form with message (if any)
    return render_template('create_account.html')

@bp.route('/profile', methods=['GET'])
@auth_required
def profile(user: User):
    return render_template("profile.html", user=user)

@bp.route('/update_profile', methods=['POST'])
@auth_required
def update_profile(user: User):
    # Update the user's profile based on the form data
    if 'name' in request.form:
        user.name = request.form['name']
    if 'email' in request.form:
        user.email = request.form['email']
    if 'password' in request.form and request.form['password']:
        hashed_password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        user.password = hashed_password

    # Save the updated user information to the database
    user_collection.update_one({'name_id': user.name_id}, {'$set': user.json()})

    # Provide feedback to the user
    flash("Profile updated successfully.")
    return redirect(url_for('auth.profile'))

@bp.route('/logout')
def logout():
    # Remove session data, this will log the user out
    session.pop('loggedin', None)
    session.pop('next', None)
    session.pop('name_id', None)
    session.pop('admin', None)

    # Redirect to login page
    return redirect(url_for('main.index'))
