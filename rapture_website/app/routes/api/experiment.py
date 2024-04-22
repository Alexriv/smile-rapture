from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify, current_app
from flask_socketio import emit

from app.utils.kube import deploy_experiment
from app.services.experiments import admin_experiment_queue
from app.services.node import get_latest_nodes, kube_nodes
from app.services.db import config_collection
from app.models import User, Experiment, NodeType, KubernetesNode, Node
from app.routes.api import bp as api


# Route for the request to delete an experiment
@api.route('/exp/delete/', methods=['POST'])
def exp_delete():
    experiment_uuid = str(request.json['uuid'])
    experiment = Experiment.get_by_id(experiment_uuid)

    deleted = experiment.delete()

    if deleted:
        return jsonify({"status": "success"})

    return jsonify({"status": "failed"})
