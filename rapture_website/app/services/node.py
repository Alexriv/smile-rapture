from flask import current_app

from app.models import KubernetesNode, NodeType
from app.services.kube import core_v1

kube_nodes: list[KubernetesNode] = []


def get_latest_nodes():

    if current_app.config['FAKE_MODE']:
        kube_nodes.clear()
        kube_nodes.append(KubernetesNode(type=NodeType.UNASSIGNED, hostname='fake-rpi.local'))
        kube_nodes.append(KubernetesNode(type=NodeType.UNASSIGNED, hostname='fake-bot.local'))
        return

    nodes = core_v1.list_node()

    for node in nodes.items:
        known = False
        for kube_node in kube_nodes:
            if kube_node.hostname == node.metadata.name:
                known = True
                break
        if not known:
            kube_nodes.append(KubernetesNode(type=NodeType.UNASSIGNED, hostname=node.metadata.name))
