import typing as t


_OPENAPI_METHODS = frozenset({"get", "post", "put", "patch", "delete", "options", "head", "trace"})
_SUMMARY_PREFIX = "[NOT RECOMMENDED]"
_NOTICE = (
    "**Notice:** This endpoint is still in early development and is not recommended for use. "
    "Prefer the corresponding v1 endpoint where available."
)


def _annotate_summary(existing: str | None) -> str:
    if not existing:
        return _SUMMARY_PREFIX
    if existing.startswith(f"{_SUMMARY_PREFIX} "):
        return existing
    return f"{_SUMMARY_PREFIX} {existing}"


def _annotate_description(existing: str | None) -> str:
    if existing and existing.startswith(_NOTICE):
        return existing
    if existing:
        return f"{_NOTICE}\n\n{existing}"
    return _NOTICE


def annotate_v2_openapi(schema: dict[str, t.Any]) -> dict[str, t.Any]:
    """Add the v2 usage notice to the already-filtered OpenAPI schema."""
    for path_item in schema.get("paths", {}).values():
        for method, operation in path_item.items():
            if method not in _OPENAPI_METHODS or not isinstance(operation, dict):
                continue
            operation["summary"] = _annotate_summary(operation.get("summary"))
            operation["description"] = _annotate_description(operation.get("description"))

    return schema
