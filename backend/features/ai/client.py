import json
import os
from typing import TypeVar

from google import genai
from pydantic import BaseModel


ResponseModel = TypeVar("ResponseModel", bound=BaseModel)


def request_structured_output(
    *,
    instructions: str,
    context: dict,
    response_schema: type[ResponseModel],
) -> ResponseModel:
    client = genai.Client(
        api_key=os.environ.get("GEMINI_API_KEY"),
    )

    try:
        interaction = client.interactions.create(
            model="models/gemini-3.8-flash",
            input=(
                f"{instructions}\n\n"
                f"Supplied context:\n{json.dumps(context)}"
            ),
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": response_schema.model_json_schema(),
            },
            timeout=300.0,
        )

        data = json.loads(interaction.output_text)
        return response_schema.model_validate(data)

    finally:
        client.close()