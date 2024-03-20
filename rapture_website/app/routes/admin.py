from flask import render_template, flash, Blueprint, current_app

from app.services.node import get_latest_nodes
from app.services.auth import admin_required
from app.models import User, Experiment

# Create a Blueprint for auth-related routes
bp = Blueprint('admin', __name__, url_prefix='/admin')


@bp.route('/')
@admin_required
def admin(user: User):
    experiments = Experiment.get_all()

    for experiment in experiments:
        try:
            experiment.update()
        except Exception as E:
            flash(f"Error: Experiment update failed '{experiment.experiment_uuid}' {str(E)}")

    return render_template('admin.html', user=user,
                           experiments=experiments, users=User.get_all())


@bp.route('/nodes', methods=['GET'])
@admin_required
def show_all_nodes(user: User):
    try:
        nodes = get_latest_nodes()
    except Exception as E:
        flash(f"Error: Could not get node list {str(E)}")
        nodes = []

    return render_template("nodes.html", nodes=nodes)