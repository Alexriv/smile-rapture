import os
import shutil
from models import *
import yaml
import kubernetes

REGISTRY_ADDRESS = "130.191.161.13:5000"


def __create_dockerfile():
    f = open("dockerfile", "w")
    f.write("FROM python:3.11.5\n")
    f.write("WORKDIR /code\n")
    f.write("COPY requirements.txt .\n")
    f.write("RUN pip install -r requirements.txt\n")
    f.write("COPY src/ .\n")
    f.write("CMD [ \"python\", \"./main.py\" ]")
    f.close()


def __generate_image(user_name: str, container: Container):
    # remove remnants of previous container
    try:
        shutil.rmtree("src/")
    except:
        pass
    try:
        os.remove("requirements.txt")
    except:
        pass

    # copy container files to build directory
    shutil.copytree(container.src_dir, "src/")
    shutil.copy(container.python_requirements, "requirements.txt")

    # build and push container image
    os.system(f"docker buildx build --push --platform linux/arm64,linux/amd64 --tag {REGISTRY_ADDRESS}/{user_name}/{container.registry_tag} . --output=type=registry,registry.insecure=true")


def __create_yaml(user_name: str, containers: list):
    documents = [{
        "apiVersion": "v1",
        "kind": "Namespace",
        "metadata": {
            "name": user_name
        }
    }]
    
    # Loop through each container to create Jobs
    for container in containers:
        job_document = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": container.name,
                "namespace": user_name,
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
                            "image": f"{REGISTRY_ADDRESS}/{user_name}/{container.registry_tag}",
                            "imagePullPolicy": "Always"
                        }],
                        "restartPolicy": "Never"
                    }
                },
                "backoffLimit": 0
            }
        }
        documents.append(job_document)
        
        # Service document if container has ports
        if len(container.ports) > 0:
            service_document = {
                "apiVersion": "v1",
                "kind": "Service",
                "metadata": {
                    "name": f"{container.name}-svc",
                    "namespace": user_name,
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


def deploy_experiment(experiment: Experiment):
    os.system(f"sudo k3s kubectl delete namespace {experiment.created_by}")
    __create_dockerfile()

    containers = []

    lines = []
    with open("../helper-app/src/main.py", "r") as f:
        lines = f.readlines()
    with open("../helper-app/src/main.py", "w") as f:
        lines[0] = f"EXPERIMENT_UUID = \"{experiment.experiment_uuid}\"\n"
        f.writelines(lines)
    smile_container = Container(src_dir="../helper-app/src/", python_requirements="../helper-app/requirements.txt", registry_tag="smile-app", ports=[5555], status=ContainerStatus.PENDING, name="smile-app")
    __generate_image(experiment.created_by, smile_container)
    containers.append(smile_container)

    for node in experiment.nodes:
        for container in node.containers:
            __generate_image(experiment.created_by, container)
            containers.append(container)

    __create_yaml(experiment.created_by, containers)
    os.system("sudo k3s kubectl create -f generated.yaml")


def update_experiment_status(experiment: Experiment):
    if experiment.status == ExperimentStatus.COMPLETED or experiment.status == ExperimentStatus.STOPPED:
        return
    kubernetes.config.load_kube_config(config_file="/etc/rancher/k3s/k3s.yaml")
    batch_v1 = kubernetes.client.BatchV1Api()
    jobs = batch_v1.list_namespaced_job(experiment.created_by)

    job_list: dict[str, Container] = {}
    for node in experiment.nodes:
        for container in node.containers:
            job_list[container.name] = container

    all_jobs_succeeded = True
    any_jobs_failed = False
    for job in jobs.items:
        # ignore smile-app, because the user can't track this
        if job.metadata.name == "smile-app":
            continue
        if job.status.active:
            all_jobs_succeeded = False
            experiment.status = ExperimentStatus.RUNNING
            job_list[job.metadata.name].status = ContainerStatus.RUNNING
        if job.status.succeeded:
            job_list[job.metadata.name].status = ContainerStatus.SUCCEEDED
        if job.status.failed:
            job_list[job.metadata.name].status = ContainerStatus.FAILED
            any_jobs_failed = True
    if all_jobs_succeeded:
        experiment.status = ExperimentStatus.COMPLETED
    if any_jobs_failed:
        experiment.status = ExperimentStatus.STOPPED


# below is only for debugging/development
if __name__ == "__main__":
    container = Container("../test-apps/hello-world/src/", "../test-apps/hello-world/requirements.txt", "hello-world", [], ContainerStatus.PENDING, "hello-world")
    nodes = [Node(NodeType.DRONE_ARM64, [container])]
    experiment = Experiment("1234", nodes, ExperimentStatus.NOT_READY, [], time.time(), "admin")
    deploy_experiment(experiment)