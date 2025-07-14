import json
import os
import yaml

def get_unstructured_playbook_file_path(playbook_file_name):
    return f"../playbooks/unstructured/{playbook_file_name}"


def get_unstructured_playbook_content(playbook_file_name):
    return get_file_content(get_unstructured_playbook_file_path(playbook_file_name))


def get_translated_playbook_file_path(playbook_file_name):
    return f"../playbooks/translated/{playbook_file_name}"


def get_translated_playbook_content(playbook_file_name):
    return get_file_content(get_translated_playbook_file_path(playbook_file_name))


def get_file_content(path):
    file_exists = os.path.isfile(path)
    if not file_exists:
        return None
    
    file_extension = os.path.splitext(path)[1].lower()
    with open(path, "r") as file:
        if file_extension == ".json":
            return json.load(file)
        elif file_extension in [".yaml", ".yml"]:
            return yaml.safe_load(file)
        else:
            raise ValueError("Unsupported file type")
   