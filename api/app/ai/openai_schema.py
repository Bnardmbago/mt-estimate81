from typing import Any

from pydantic import BaseModel


def build_form_fields_suggestion_schema(field_keys: list[str]) -> dict[str, Any]:
    properties = {key: {"type": "string"} for key in field_keys}
    return {
        "type": "object",
        "properties": {
            "form_data": {
                "type": "object",
                "properties": properties,
                "required": field_keys,
                "additionalProperties": False,
            },
            "generation_notes": {"type": "string"},
        },
        "required": ["form_data", "generation_notes"],
        "additionalProperties": False,
    }


def build_openai_strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    schema = model.model_json_schema()
    schema.pop("$schema", None)
    _apply_strict(schema)
    return schema


def _apply_strict(node: dict[str, Any]) -> None:
    if not isinstance(node, dict):
        return

    for key in ("$defs", "definitions"):
        if key in node:
            for definition in node[key].values():
                _apply_strict(definition)

    if node.get("type") == "object" or "properties" in node:
        node["additionalProperties"] = False
        properties = node.get("properties", {})
        if properties:
            node["required"] = list(properties.keys())
        for property_schema in properties.values():
            _apply_strict(property_schema)

    items = node.get("items")
    if isinstance(items, dict):
        _apply_strict(items)
    elif isinstance(items, list):
        for item in items:
            _apply_strict(item)

    for composite_key in ("anyOf", "oneOf", "allOf"):
        if composite_key in node:
            for item in node[composite_key]:
                _apply_strict(item)
