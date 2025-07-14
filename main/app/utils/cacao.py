from typing import List, Optional
from langchain_core.pydantic_v1 import BaseModel, Field

from datetime import datetime

from app.utils.cacao_spec import (
    PLAYBOOK_ACTIVITIES_DESCRIPTION,
    PLAYBOOK_ACTIVITIES_VALID,
    PLAYBOOK_CREATED_DESCRIPTION,
    PLAYBOOK_DESCRIPTION_DESCRIPTION,
    PLAYBOOK_LABELS_DESCRIPTION,
    PLAYBOOK_MODIFIED_DESCRIPTION,
    PLAYBOOK_NAME_DESCRIPTION,
    PLAYBOOK_TYPES_DESCRIPTION,
    PLAYBOOK_TYPES_VALID,
)
from app.utils.prompts import KNOWLEDGE_PLACEHOLDER


class BasePlaybook(BaseModel):
    def __getitem__(self, name):
        return getattr(self, name)


class NamePlaybook(BasePlaybook):
    name: Optional[str] = Field(
        default=None,
    )
    reason: Optional[str] = Field(default=None)


class DescriptionPlaybook(BasePlaybook):
    description: Optional[str] = Field(
        default=None,
    )
    reason: Optional[str] = Field(default=None)


class PlaybookTypes(BasePlaybook):
    class PlaybookTypeExtraction(BaseModel):
        type: str = Field(default=None)
        reason: str = Field(default=None)

    playbook_types: List[PlaybookTypeExtraction] = Field(default=None)


class PlaybookActivities(BasePlaybook):
    class PlaybookActivityExtraction(BaseModel):
        activity: str = Field(default=None)
        reason: str = Field(default=None)

    playbook_activities: List[PlaybookActivityExtraction] = Field(default=None)


class PlaybookLabels(BasePlaybook):
    labels: Optional[list[str]] = Field(
        default=None,
    )
    reason: Optional[str] = Field(default=None)


class PlaybookCreated(BasePlaybook):
    created: Optional[datetime] = Field(
        default=None,
    )
    reason: Optional[str] = Field(default=None)


class PlaybookModified(BasePlaybook):
    modified: Optional[datetime] = Field(
        default=None,
    )
    reason: Optional[str] = Field(default=None)


INFER_VALUE_OR_NULL = (
    lambda field: f"Infer the value for the '{field}' field, if you can't do it, please provide null."
)

field_config_mapping = {
    "name": {
        "documents_to_include": 5,
        "schema": NamePlaybook,
        "field_name": "name",
        "field_type": "string",
        "question": f"""
            What is the CACAO translation for the supplied playbook? 
            Extract the 'name' field.
            {KNOWLEDGE_PLACEHOLDER}
            {INFER_VALUE_OR_NULL("name")}
        """,
        "knowledge": [
            {
                "specification": PLAYBOOK_NAME_DESCRIPTION,
            }
        ],
    },
    "description": {
        "documents_to_include": 5,
        "schema": DescriptionPlaybook,
        "field_name": "description",
        "field_type": "string",
        "question": f"""
            What is the CACAO translation for the supplied playbook? 
            Extract the 'description' field.
            {KNOWLEDGE_PLACEHOLDER}
            {INFER_VALUE_OR_NULL("description")}
        """,
        "knowledge": [
            {
                "specification": PLAYBOOK_DESCRIPTION_DESCRIPTION,
            }
        ],
    },
    "playbook_types": {
        "documents_to_include": 5,
        "schema": PlaybookTypes,
        "field_name": "type",
        "field_type": "string",
        "question": f"""
            What is the CACAO translation for the supplied playbook? 
            Extract a list of playbook_types.
            {KNOWLEDGE_PLACEHOLDER}
            {INFER_VALUE_OR_NULL("playbook_types")}
        """,
        "knowledge": [
            {
                "specification": PLAYBOOK_TYPES_DESCRIPTION,
                "valid_message": "Here are the valid 'playbook_types' values:",
                "valid_values": PLAYBOOK_TYPES_VALID,
            }
        ],
        "multiple": {
            "array_name": "playbook_types",
            "entity_name": "playbook type",
        },
        "mapResponse": lambda response: (
            [
                (
                    item["type"]
                    if isinstance(item, dict) and item.get("type") is not None
                    else str(item)
                )
                for item in (response.get("playbook_types", []) or [])
                if item is not None
            ]
            if response is not None
            else []
        ),
    },
    "playbook_activities": {
        "documents_to_include": 5,
        "schema": PlaybookActivities,
        "field_name": "activity",
        "field_type": "string",
        "question": f"""
            What is the CACAO translation for the supplied playbook? 
            Extract a list of playbook_activities.
            {KNOWLEDGE_PLACEHOLDER}
            {INFER_VALUE_OR_NULL("playbook_activities")}
        """,
        "knowledge": [
            {
                "specification": PLAYBOOK_ACTIVITIES_DESCRIPTION,
                "valid_message": "Here are the valid 'playbook_activities' values:",
                "valid_values": PLAYBOOK_ACTIVITIES_VALID,
            }
        ],
        "multiple": {
            "array_name": "playbook_activities",
            "entity_name": "playbook activity",
        },
        "mapResponse": lambda response: (
            [
                (
                    item["activity"]
                    if isinstance(item, dict) and item.get("activity") is not None
                    else str(item)
                )
                for item in (response.get("playbook_activities", []) or [])
                if item is not None
            ]
            if response is not None
            else []
        ),
    },
    "labels": {
        "documents_to_include": 5,
        "schema": PlaybookLabels,
        "field_name": "labels",
        "field_type": "array of strings",
        "question": f"""
            What is the CACAO translation for the supplied playbook? 
            Extract the 'labels' field.
            {KNOWLEDGE_PLACEHOLDER}
            {INFER_VALUE_OR_NULL("labels")}
        """,
        "knowledge": [
            {
                "specification": PLAYBOOK_LABELS_DESCRIPTION,
            }
        ],
    },
    "created": {
        "documents_to_include": 5,
        "schema": PlaybookCreated,
        "field_name": "created",
        "field_type": "datetime",
        "question": f"""
            What is the CACAO translation for the supplied playbook? 
            Extract the 'created' field.
            {KNOWLEDGE_PLACEHOLDER}
            Make sure that the extracted value for the 'created' field is present in the supplied playbook.
            {INFER_VALUE_OR_NULL("created")}
        """,
        "knowledge": [
            {
                "specification": PLAYBOOK_CREATED_DESCRIPTION,
            }
        ],
    },
    "modified": {
        "documents_to_include": 5,
        "schema": PlaybookModified,
        "field_name": "modified",
        "field_type": "datetime",
        "question": f"""
            What is the CACAO translation for the supplied playbook? 
            Extract the 'modified' field.
            {KNOWLEDGE_PLACEHOLDER}
            Make sure that the extracted value for the 'modified' field is present in the supplied playbook.
            {INFER_VALUE_OR_NULL("modified")}
        """,
        "knowledge": [
            {
                "specification": PLAYBOOK_MODIFIED_DESCRIPTION,
            }
        ],
    },
}
