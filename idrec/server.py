import tempfile
from typing import *
from pathlib import Path

import streamlit as st
from PIL import Image
from openai import OpenAI


CLIENT = OpenAI(api_key=st.secrets.openai_api_key)

# Load config
ALLOWED_EMAILS = st.secrets.allowed_emails


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

    return response.output_text


def send_for_annotation(image: Image.Image):
    """Send image to external annotation server and return response text."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg") as fp:
            image.save(fp)
            response = request_id(CLIENT, fp.name)

        return response
    except Exception as e:
        return f"⚠️ Request failed: {e.with_traceback(None)}"


if not st.user.is_logged_in:
    if st.button("Log in"):
        st.login()
    st.stop()
else:
    user_email = st.user.email  # or appropriate attribute

    if user_email not in ALLOWED_EMAILS:
        st.error("Access denied: email not whitelisted.")
        st.stop()

st.set_page_config(page_title="Phone Camera Annotation App")

st.title("📸 Phone Camera Annotation App")
st.write("Take a photo with your phone and send it to the annotation server.")


uploaded_image = st.camera_input("Take a photo")

if uploaded_image is not None:
    if st.button("Send to Annotation Server"):
        # Convert image to bytes
        image = Image.open(uploaded_image)

        # Send POST request
        with st.spinner("Sending image to server..."):
            with tempfile.NamedTemporaryFile(suffix=".jpg") as fp:

                image.save(fp)
                response = request_id(CLIENT, fp.name)

        st.markdown(response.output_text)

else:
    st.info("Please take a photo using your phone camera above.")
