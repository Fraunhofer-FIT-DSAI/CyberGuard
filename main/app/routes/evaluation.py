from typing import Literal
from langserve import CustomUserType
import json
from app.routes.main import AVAILABLE_UNSTRUCTURED_PLAYBOOKS, Model
from app.evaluation.semantic import evaluate_playbook as semantic_evaluate_playbook
from app.evaluation.syntactic import evaluate_playbook as syntactic_evaluate_playbook
from app.evaluation.graph import handler as graph_evaluation
from app.routes.evaluation_script import get_structured_playbook


class Dependencies(CustomUserType):
    playbook_file_name: AVAILABLE_UNSTRUCTURED_PLAYBOOKS = (
        "AWS_IAM_Account_Locking.json"
    )
    model: Model = "gpt-4o-mini-2024-07-18"
    flow: Literal["syntactic", "semantic", "graph"] = "graph"
    vendor: Literal["splunk", "demisto", "fortinet"] = "splunk"
    text: str = ""


def handler(dependencies: Dependencies):
  
    ground_truth = get_structured_playbook(
        dependencies.playbook_file_name, dependencies.vendor
    )
    translation = json.loads(dependencies.text)

    if dependencies.flow == "syntactic":
        return syntactic_evaluate_playbook(translation)

    if dependencies.flow == "semantic":
        return semantic_evaluate_playbook(translation, ground_truth)

    if dependencies.flow == "graph":
        return graph_evaluation(translation["workflow"], ground_truth["workflow"])
