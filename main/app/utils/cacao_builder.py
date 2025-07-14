from uuid import uuid4


def insert_cacao_static_fields(cacao_playbook):
    cacao_playbook["type"] = "playbook"
    cacao_playbook["spec_version"] = "cacao-2.0"
    cacao_playbook["id"] = generate_cacao_id("playbook")
    return cacao_playbook

def generate_workflow():
    end_step = generate_end_step()
    action_step1 = generate_action_step(
        name="Action Step 1",
        description="Description 1",
        on_completion=get_step_id(end_step),
    )
    start_step = generate_start_step(on_completion=get_step_id(action_step1))

    return {
        get_step_id(start_step): start_step[get_step_id(start_step)],
        get_step_id(action_step1): action_step1[get_step_id(action_step1)],
        get_step_id(end_step): end_step[get_step_id(end_step)],
    }


def get_start_step_id(workflow):
    for key, value in workflow.items():
        if "type" in value and value["type"] == "start":
            return key
    return workflow["workflow_start"] if "workflow_start" in workflow else None


def generate_start_step(name="Start", on_completion=None):
    return {
        generate_cacao_id("start"): {
            "type": "start",
            "name": name,
            "on_completion": on_completion,
        }
    }


def generate_action_step(
    name="Action Step", description="Description", on_completion=None
):
    return {
        generate_cacao_id("action"): {
            "type": "action",
            "name": name,
            "description": description,
            "on_completion": on_completion,
        }
    }


def generate_end_step(name="End"):
    return {
        generate_cacao_id("end"): {
            "type": "end",
            "name": name,
        }
    }


def get_step_id(step):
    return list(step.keys())[0]


def generate_cacao_id(prefix, uuid=""):
    return f"{prefix}--{generate_id() if not uuid else uuid}"


def generate_id():
    return str(uuid4())


from uuid import UUID


def is_valid_uuid(uuid_to_test, version=4):
    uuid_to_test = str(uuid_to_test)
    try:
        uuid_obj = UUID(uuid_to_test, version=version)
    except ValueError:
        return False
    return str(uuid_obj) == uuid_to_test
