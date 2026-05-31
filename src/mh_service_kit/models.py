from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class AgentRunRequest(BaseModel):
    user_input: list[dict] = []
    tools: list[dict] = []
    memory: list[dict] = []
    system_prompt: str = ""
    config: dict = {}


class ToolExecuteRequest(BaseModel):
    args: dict = {}
    tool_call_id: str = ""


def parameters_from_model(model: type[BaseModel]) -> dict[str, Any]:
    """Convert a Pydantic BaseModel to an OpenAI-compatible tool parameters JSON Schema dict.

    Example:
        >>> from pydantic import BaseModel, Field
        >>> class CalcParams(BaseModel):
        ...     expression: str = Field(description="Math expression")
        >>> parameters_from_model(CalcParams)
        {'type': 'object', 'properties': {'expression': {'type': 'string', 'description': 'Math expression', 'title': 'Expression'}}, 'required': ['expression']}
    """
    schema = model.model_json_schema()
    return {
        "type": "object",
        "properties": schema.get("properties", {}),
        "required": schema.get("required", []),
    }


def validate_args(
    args: dict[str, Any],
    parameters: dict[str, Any] | None,
    params_model: type[BaseModel] | None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Validate tool arguments against the declared schema.

    Returns (validated_args, error_message). If valid, validated_args is the
    cleaned/coerced dict and error_message is None. Otherwise validated_args
    is None and error_message describes the problem.
    """
    if params_model is not None:
        try:
            instance = params_model.model_validate(args)
            return instance.model_dump(mode="python"), None
        except Exception as e:
            return None, str(e)

    if parameters:
        required = parameters.get("required", [])
        props = parameters.get("properties", {})

        missing = [f for f in required if f not in args]
        if missing:
            return None, f"Missing required parameters: {', '.join(missing)}"

        for key, value in args.items():
            prop = props.get(key, {})
            enum_vals = prop.get("enum")
            if enum_vals is not None and value not in enum_vals:
                return (
                    None,
                    f"Parameter '{key}' must be one of: {', '.join(str(v) for v in enum_vals)}",
                )

    return args, None
