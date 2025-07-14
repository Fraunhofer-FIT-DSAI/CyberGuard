from jsonschema import Draft7Validator
import urllib.request, json

SCHEMAS_URL = (
    "https://raw.githubusercontent.com/devicedev/cacao-json-schemas/main/schemas/"
)

with urllib.request.urlopen(f"{SCHEMAS_URL}/playbook.json") as url:
    playbook_schema = json.load(url)


def evaluate_playbook(translation):
    validator = Draft7Validator(playbook_schema)

    errors = validator.iter_errors(translation)
    errors = [
        {
            "message": error.message,
            "validator": error.validator,
            "validator_value": error.validator_value,
            "path": list(error.path),
            "cause": error.cause,
            "parent": error.parent,
            "instance": error.instance,
        }
        for error in errors
    ]

    return {
        "length": len(errors),
        "errors": errors,
    }
