import enum
import tempfile
from typing import *

from openai import OpenAI
from PIL import Image


class ResponseCodes(enum.Enum):
    NO_LABEL_CODE = "ERROR:NO-LABEL-FOUND"
    NO_FIELD_CODE = "ERROR:NO-FIELD-FOUND"
    FIELD_FOUND_CODE = "ACK:FIELD-FOUND"


USER_SYSTEM_PROMPT = "You are a VQA assistant, you help solve visual question-answering tasks provided by the user. Your answer are minimal, providing only the requested information."
USER_PROMPT = """
This picture should include a package with a shipping label on it. Among various shipping codes, it should include a field '{field_name}'.
Please, answer with only the code on the field '{field_name}', do not include additional text in your reply.
If the image does not contain a shipping label: answer with '{no_label}'.
If the image has a label, but it doesn't contain a field '{field_name}': answer with '{no_target_field}'.

Examples:
> user: <image>
  assistant: A1B-C123-ABC

> user: <image without label>
  assistant: {no_label}

> user: <image with a label without the TYPE field>
  assistant: {no_target_field}
"""


# Function to create a file with the Files API
def create_file(client: OpenAI, file_path):
    with open(file_path, "rb") as file_content:
        result = client.files.create(file=file_content, purpose="vision")
        return result.id


def request_id(client: OpenAI, image: Image, field_name: str) -> Tuple[str, ResponseCodes]:
    prompt = USER_PROMPT.format(
        no_label=ResponseCodes.NO_LABEL_CODE.value,
        no_target_field=ResponseCodes.NO_FIELD_CODE,
        field_name=field_name,
    )

    with tempfile.NamedTemporaryFile(suffix=".jpg") as fp:
        image.save(fp)
        image_data = create_file(client, fp.name)
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "file_id": image_data,
                        },
                    ],
                }
            ],
        )

        response_text = response.output_text

        try:  # Try parsing code
            return "", ResponseCodes(response_text)
        except ValueError as e:
            assert "ERROR" not in response_text and "ACK" not in response_text
            return response_text, ResponseCodes.FIELD_FOUND_CODE
