import json

from app.ai.openai_schema import build_openai_strict_schema
from app.ai.schemas import ExtractedRequirements


def _collect_object_schemas(schema: dict) -> list[dict]:
    objects: list[dict] = []

    def walk(node: dict) -> None:
        if not isinstance(node, dict):
            return
        if node.get("type") == "object" or "properties" in node:
            objects.append(node)
        for key in ("$defs", "definitions"):
            if key in node:
                for definition in node[key].values():
                    walk(definition)
        for property_schema in node.get("properties", {}).values():
            walk(property_schema)
        items = node.get("items")
        if isinstance(items, dict):
            walk(items)

    walk(schema)
    return objects


def test_openai_strict_schema_marks_objects_closed():
    schema = build_openai_strict_schema(ExtractedRequirements)
    objects = _collect_object_schemas(schema)

    assert objects, "Expected at least one object schema"
    for obj in objects:
        assert obj.get("additionalProperties") is False
        assert set(obj.get("required", [])) == set(obj.get("properties", {}).keys())


def test_openai_strict_schema_is_json_serializable():
    schema = build_openai_strict_schema(ExtractedRequirements)
    json.dumps(schema)
