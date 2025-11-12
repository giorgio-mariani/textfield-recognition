from pathlib import Path
from typing import Union
from openai import OpenAI


USER_PROMPT = """
Answer with only the code on the field 'type' in the label. Do not include additional text in your reply.
"""


# Function to create a file with the Files API
def create_file(client: OpenAI, file_path):
    with open(file_path, "rb") as file_content:
        result = client.files.create(
            file=file_content,
            purpose="vision",
        )
        return result.id


def request_id(client: OpenAI, file: Union[Path, str]) -> str:
    file = Path(file)
    assert file.exists(), file
    image_data = create_file(client, str(file))
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": USER_PROMPT},
                    {
                        "type": "input_image",
                        "file_id": image_data,
                    },
                ],
            }
        ],
    )
    print(response)
    return response.output_text
