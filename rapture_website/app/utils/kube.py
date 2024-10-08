import os
import shutil

import yaml
from flask import current_app
from flask_socketio import emit, join_room, leave_room

from app.services.node import kube_nodes
from app.models import Experiment, Container, ContainerStatus, ExperimentStatus, NodeType


def __create_dockerfile():
    f = open("dockerfile", "w")
    f.write("FROM python:3.11.5\n")
    f.write("WORKDIR /code\n")
    f.write("COPY requirements.txt .\n")
    f.write("RUN apt update\n")
    f.write("RUN apt install -y jq\n")
    f.write("RUN pip install -r requirements.txt\n")
    f.write("COPY src/ .\n")
    f.write("CMD [ \"./start.sh\" ]")
    f.close()


def __generate_image(experiment: Experiment, container: Container):
    # remove remnants of previous container
    try:
        shutil.rmtree("src/")
    except Exception as E:
        print(str(E))
        pass

    try:
        os.remove("requirements.txt")
    except Exception as E:
        print(str(E))
        pass

    # copy container files to build directory
    shutil.copytree(container.src_dir, "src/")
    shutil.copy(container.python_requirements, "requirements.txt")
    shutil.copy("../smile-module/start.sh", "src/start.sh")

    with open("src/start.sh", "r") as f:
        lines = f.readlines()

    with open("src/start.sh", "w") as f:
        lines[2] = f"experiment_id=\"{experiment.experiment_uuid}\"\n"
        lines[3] = f"container_id=\"{container.registry_tag}\"\n"
        f.writelines(lines)

    # build and push container image
    os.system(
        f"docker buildx build --push --platform linux/arm64,linux/amd64 --tag {current_app.config['REGISTRY_URI']}/{experiment.created_by}/{container.registry_tag} . --output=type=registry,registry.insecure=true")


def __create_yaml(experiment: Experiment, containers: list[Container]):
    documents = [{
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": {
            "name": experiment.created_by
        }
    }]

    # Loop through each container to create Jobs
    for container in containers:
        job_document = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": container.name,
                "namespace": experiment.created_by,
                "labels": {
                    "k8s-app": container.name
                },
            },
            "spec": {
                "template": {
                    "metadata": {
                        "labels": {
                            "k8s-app": container.name
                        }
                    },
                    "spec": {
                        "containers": [{
                            "name": container.name,
                            "image": f"{current_app.config['REGISTRY_URI']}/{experiment.created_by}/{container.registry_tag}",
                            "imagePullPolicy": "Always"
                        }],
                        "restartPolicy": "Never",
                        "nodeName": f"{container.hostname}"
                    }
                },
                "backoffLimit": 0
            }
        }
        if "smile" in container.name:
            pass
        else:
            job_document["spec"]["template"]["spec"]["containers"][0]["securityContext"] = {"privileged": True}
            job_document["spec"]["template"]["spec"]["containers"][0]["volumeMounts"] = [{"mountPath": "/dev/video0", "name": "dev-video0"}]
            job_document["spec"]["template"]["spec"]["volumes"] = [{"name": "dev-video0", "hostPath": {"path": "/dev/video0"}}]

        documents.append(job_document)

        # Service document if container has ports
        if len(container.ports) > 0:
            service_document = {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {
                    "name": f"{container.name}-svc",
                    "namespace": experiment.created_by,
                    "labels": {
                        "k8s-app": f"{container.name}-svc"
                    },
                },
                "spec": {
                    "selector": {
                        "k8s-app": container.name
                    },
                    "ports": [{"port": port} for port in container.ports]
                }
            }
            documents.append(service_document)

    # Write to YAML file
    with open("generated.yaml", "w") as file:
        yaml.dump_all(documents, file)


def __select_random_node(node_type: NodeType):
    for kubernetes_node in kube_nodes:
        if not kubernetes_node.is_ready():
            continue
        if kubernetes_node.type == node_type:
            return kubernetes_node
    raise Exception("No available nodes __select_random_node")


def deploy_experiment(experiment: Experiment):
    # emit('deploy_event', {'msg': 'Starting Deploy...', 'color': 'green'}, room=f'{experiment.experiment_uuid}')
    os.system(f"sudo k3s kubectl delete namespace {experiment.created_by}")
    print("creating dockerfile...", end=" ")
    __create_dockerfile()
    # emit('deploy_event', {'msg': 'Dockerfile Created', 'color': 'green'}, room=f'{experiment.experiment_uuid}')
    print("done")

    containers = []

    # Create RAPTURE SMILE app
    with open("../rapture-smile-app/src/main.py", "r") as f:
        lines = f.readlines()
    with open("../rapture-smile-app/src/main.py", "w") as f:
        lines[0] = f"EXPERIMENT_UUID = \"{experiment.experiment_uuid}\"\n"
        f.writelines(lines)

    rapture_smile_app = Container(src_dir="../rapture-smile-app/src/",
                                  python_requirements="../rapture-smile-app/requirements.txt",
                                  registry_tag=f"rapture-smile-app-{experiment.experiment_uuid}", ports=[5555],
                                  status=ContainerStatus.PENDING, name=f"rapture-smile-app",
                                  hostname=__select_random_node(NodeType.COMPUTE_PI).hostname)

    print("creating Rapture Smile App image...", end=" ")
    __generate_image(experiment, rapture_smile_app)
    print("done")
    # emit('deploy_event', {'msg': 'SMILE Helper App Deployed', 'color': 'green'}, room=f'{experiment.experiment_uuid}')
    containers.append(rapture_smile_app)

    for node in experiment.nodes:
        if node.type == NodeType.ROVER_PI:
            with open("../rover-smile-app/src/main.py", "r") as f:
                lines = f.readlines()
            with open("../rover-smile-app/src/main.py", "w") as f:
                lines[0] = f"ROBOT_NAME = \"{node.kubernetes_node.hostname}\"\n"
                f.writelines(lines)
            rover_smile_app = Container(src_dir="../rover-smile-app/src/",
                                        python_requirements="../rover-smile-app/requirements.txt",
                                        registry_tag=f"{node.nickname}-rover-smile-app-{experiment.experiment_uuid}",
                                        ports=[5555],
                                        status=ContainerStatus.PENDING, name=f"{node.nickname}-rover-smile-app",
                                        hostname=node.kubernetes_node.hostname)
            print(f"creating Rover Smile App image for {node.nickname}...", end=" ")
            __generate_image(experiment, rover_smile_app)
            print("done")
            containers.append(rover_smile_app)

    # Create user apps
    used_nodes = []
    for node in experiment.nodes:
        if node.kubernetes_node is None:
            kubernetes_node = None
            while True:
                kubernetes_node = __select_random_node(node.type)
                if kubernetes_node not in used_nodes:
                    break
            used_nodes.append(kubernetes_node)
            print(kubernetes_node)
            node.kubernetes_node = kubernetes_node
        for container in node.containers:
            container.hostname = node.kubernetes_node.hostname
            print(f"creating user {container.name} App image...", end=" ")
            robot_names = ""
            for node in experiment.nodes:
                if node.type == NodeType.ROVER_PI:
                    robot_names += f"\"{node.nickname}\","
            with open(container.src_dir + "/smile.py", "a") as f:
                f.write(f"\n__init(\"{experiment.created_by}\", [{robot_names}])")
            __generate_image(experiment, container)
            print("done")
            containers.append(container)

    # emit('deploy_event', {'msg': 'App Images Created', 'color': 'green'}, room=f'{experiment.experiment_uuid}')

    print("creating k3s deployment yaml...", end=" ")
    __create_yaml(experiment, containers)
    print("done")
    print("deploying...", end=" ")
    # emit('deploy_event', {'msg': 'Kubernetes Deploy Started', 'color': 'green'}, room=f'{experiment.experiment_uuid}')
    os.system("sudo k3s kubectl create -f generated.yaml")
    print("done")
    experiment.status = ExperimentStatus.RUNNING
    # emit('deploy_event', {'msg': 'Experiment Running', 'color': 'green'}, room=f'{experiment.experiment_uuid}')
