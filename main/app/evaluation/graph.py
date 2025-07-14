import networkx as nx
from jellyfish import damerau_levenshtein_distance
import matplotlib.pyplot as plt
import os



def evaluate_similarity(field, ground_truth, translation, similarities):
    metric = similarities[field]
    if field not in ground_truth:
        if field not in translation:
            return 1
        return 0
    if field not in translation:
        return 0

    if ground_truth[field] is None and translation[field] is None:
        return 1

    return metric(
        ground_truth[field],
        translation[field],
    )


def absolute_similarity(a, b):
    return a == b


def damerau_levenshtein_similarity(a, b):
    if not a or not b:
        return 0
    return 1 - round(damerau_levenshtein_distance(a, b) / max(len(a), len(b)), 2)


def node_match(node1, node2):
    similarities = {
        "name": damerau_levenshtein_similarity,
        "type": absolute_similarity,
    }

    # if both nodes have no name, compare type
    if node1.get("name") is None and node2.get("name") is None:
        similarity_value = evaluate_similarity("type", node1, node2, similarities)
        if similarity_value:
            # print("node_matching 2", node1.get("type"), "-", node2.get("type"))
            return True
        return False

    # compare by name with threshold
    similarity_value = evaluate_similarity("name", node1, node2, similarities)

    threshold = 0.5
    if similarity_value >= threshold:
        # print("node_matching 1", node1.get("name"), "-", node2.get("name"))
        return True

    return False


def node_ins_cost(a):
    return 1


def node_del_cost(a):
    return 1


def edge_match(edge1, edge2):
    return edge1["connection"] == edge2["connection"]


def edge_ins_cost(a):
    return 1


def edge_del_cost(a):
    return 1


def handler(translation_workflow, ground_truth_workflow):
    translation_graph = create_graph(translation_workflow)
    ground_truth_graph = create_graph(ground_truth_workflow)

    edit_distance = nx.graph_edit_distance(
        translation_graph,
        ground_truth_graph,
        edge_match=edge_match,
        edge_ins_cost=edge_ins_cost,
        edge_del_cost=edge_del_cost,
        node_match=node_match,
        node_ins_cost=node_ins_cost,
        node_del_cost=node_del_cost,
    )
    print("Edit Distance:", edit_distance)

    max_edit_distance = (
            translation_graph.number_of_nodes() + ground_truth_graph.number_of_nodes() +
            translation_graph.number_of_edges() + ground_truth_graph.number_of_edges()
        )

    # Normalize the edit distance
    normalized_edit_distance = edit_distance / max_edit_distance if max_edit_distance > 0 else 0
    print("Normalized Edit Distance:", normalized_edit_distance)

    if os.environ.get("ENVIRONMENT") == "prod":
        return {"graph_edit_distance": normalized_edit_distance}

    labels_translation = {
        node: f"{get_id(node, data)[:10]}\n{data['type']}"
        for node, data in translation_graph.nodes(data=True)
    }

    edge_labels_translation = {
        (u, v): data["connection"] for u, v, data in translation_graph.edges(data=True)
    }

    labels_ground_truth = {
        node: f"{get_id(node, data)[:10]}\n{data['type']}"
        for node, data in ground_truth_graph.nodes(data=True)
    }

    edge_labels_ground_truth = {
        (u, v): data["connection"] for u, v, data in ground_truth_graph.edges(data=True)
    }
    # Increase the spacing between nodes by adjusting the `k` parameter
    pos_translation = nx.spring_layout(translation_graph, k=2)
    pos_ground_truth = nx.spring_layout(ground_truth_graph, k=2)

    # Draw the translation graph
    plt.figure(figsize=(18, 12))
    plt.get_current_fig_manager().full_screen_toggle()
    plt.subplot(121)
    nx.draw(
        translation_graph,
        pos_translation,
        with_labels=True,
        labels=labels_translation,
        node_size=3000,
        node_color="lightblue",
        font_size=10,
    )
    nx.draw_networkx_edge_labels(
        translation_graph,
        pos_translation,
        edge_labels=edge_labels_translation,
        font_color="red",
    )
    plt.title("Translation Graph")

    # Draw the ground truth graph
    plt.subplot(122)
    nx.draw(
        ground_truth_graph,
        pos_ground_truth,
        with_labels=True,
        labels=labels_ground_truth,
        node_size=3000,
        node_color="lightgreen",
        font_size=10,
    )
    nx.draw_networkx_edge_labels(
        ground_truth_graph,
        pos_ground_truth,
        edge_labels=edge_labels_ground_truth,
        font_color="red",
    )
    plt.title("Ground Truth Graph")

    plt.show()

    return edit_distance


def create_graph(workflow):
    graph = nx.DiGraph()

    for step_id, step in workflow.items():
        graph.add_node(
            get_id(step_id, step),
            name=step.get("name", None),
            description=step.get("description", None),
            type=step.get("type", None),
            on_completion=step.get("on_completion", None),
            on_success=step.get("on_success", None),
            on_failure=step.get("on_failure", None),
            condition=step.get("condition", None),
            on_true=step.get("on_true", None),
            on_false=step.get("on_false", None),
        )

    for step_id, step in workflow.items():
        possible_edge_attributes = [
            "on_completion",
            "on_success",
            "on_failure",
            "on_true",
            "on_false",
        ]
        for edge_attribute in possible_edge_attributes:
            if is_valid_connection(workflow, step, edge_attribute):
                step_id = get_id(step_id, step)
                step_id2 = get_id(step[edge_attribute], workflow[step[edge_attribute]])
                graph.add_edge(step_id, step_id2, connection=edge_attribute)

    return graph


def get_id(step_id, step):
    if os.environ.get("ENVIRONMENT") == "dev":
        return step_id if step.get("name", None) is None else step.get("name")

    return step_id


def is_valid_connection(workflow, step, edge_attribute):
    if step.get(edge_attribute) is None:
        return False
    if workflow.get(step[edge_attribute]) is None:
        return False
    return True


translation_workflow = {
    "start--1b241a8d-df29-4e0a-834d-0ee2c5e57737": {
        "name": "Start",
        "type": "start",
        "description": "Initiate Workflow Process",
    },
    "if-condition--a8119472-69ff-4f42-bb15-a9a6a6359c9e": {
        "name": "Check for assigned to",
        "type": "if-condition",
        "description": "Verify the assignment status of a record or task.",
        "on_completion": "action--76f9622a-610d-481f-895a-1b52e4d02cfc",
        "condition": "assigned_to",
        "on_true": "action--76f9622a-610d-481f-895a-1b52e4d02cfc",
        "on_false": "action--76f9622a-610d-481f-895a-1b52e4d02cfc",
    },
    "action--76f9622a-610d-481f-895a-1b52e4d02cfc": {
        "name": "Set Recepient",
        "type": "action",
        "description": "This step sets the recipient for further processing, likely in preparation for sending an email or notification.",
        "on_completion": "action--30e8a58e-8284-4cae-b81c-2a3b4dd9090c",
    },
    "action--30e8a58e-8284-4cae-b81c-2a3b4dd9090c": {
        "name": "Get emails of the team members",
        "type": "action",
        "description": "Retrieve email addresses of all team members associated with the current record.",
        "on_completion": "action--35521d4f-0024-40a4-9a19-87b56225c41c",
    },
    "action--35521d4f-0024-40a4-9a19-87b56225c41c": {
        "name": "Send Email Using SMTP",
        "type": "action",
        "description": "This step sends an email to one or more recipients using the SMTP protocol, possibly with attachments and/or custom content.",
        "on_completion": "action--7ba93dd7-41c5-4a9b-8e58-b95d9030a87c",
    },
    "action--7ba93dd7-41c5-4a9b-8e58-b95d9030a87c": {
        "name": "Set Recepient",
        "type": "action",
        "description": "This step sets the recipient(s) based on some criteria, likely related to assignments or roles within a team.",
        "on_completion": "action--30e8a58e-8284-4cae-b81c-2a3b4dd9090c",
    },
}

ground_truth_workflow = {
    "action--e4fa6071-7a3d-44f5-9dc3-dd2b5f4634a3": {
        "name": "Configuration",
        "on_completion": "if-condition--01770550-5c9b-413e-9bab-ecbb0b397059",
        "type": "action",
    },
    "start--a50b5ce4-dfac-4782-9190-68c22a34c23e": {
        "name": "Start",
        "on_completion": "action--e4fa6071-7a3d-44f5-9dc3-dd2b5f4634a3",
        "type": "start",
    },
    "if-condition--01770550-5c9b-413e-9bab-ecbb0b397059": {
        "name": "Check for assigned to",
        "type": "if-condition",
        "condition": "{{ vars.record.assignedTo != None }}",
        "on_true": "action--935c3c24-9acd-4353-807b-c1230bfe88b6",
        "on_false": "action--dc92f412-5e4a-48a8-8c3f-5da62f9a850a",
    },
    "action--dc92f412-5e4a-48a8-8c3f-5da62f9a850a": {
        "name": "Fetch relations of the record",
        "on_completion": "action--9da0fec1-4b1c-471b-ac95-afe5ec13af0f",
        "type": "action",
    },
    "action--8ee35eca-a46d-4335-8eb1-aeb1bc27a649": {
        "name": "Send Email Using SMTP",
        "on_completion": "end--13f5dbf6-20f2-4b6c-8612-032f5408d18b",
        "type": "action",
    },
    "action--935c3c24-9acd-4353-807b-c1230bfe88b6": {
        "name": "Set Recepient",
        "on_completion": "action--8ee35eca-a46d-4335-8eb1-aeb1bc27a649",
        "type": "action",
    },
    "action--9da0fec1-4b1c-471b-ac95-afe5ec13af0f": {
        "name": "Get emails of the team members",
        "on_completion": "action--9acb3bae-7351-4d6e-961a-039c4318cf3f",
        "type": "action",
    },
    "action--9acb3bae-7351-4d6e-961a-039c4318cf3f": {
        "name": "Set All Receipients",
        "on_completion": "action--8ee35eca-a46d-4335-8eb1-aeb1bc27a649",
        "type": "action",
    },
    "end--13f5dbf6-20f2-4b6c-8612-032f5408d18b": {"type": "end"},
}

if os.environ.get("ENVIRONMENT") == "dev":
    handler(translation_workflow, ground_truth_workflow)
