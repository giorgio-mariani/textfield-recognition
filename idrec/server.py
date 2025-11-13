import io
import tempfile
from typing import *
from pathlib import Path
from datetime import datetime

import streamlit as st
from PIL import Image
from openai import OpenAI
import pandas as pd

CLIENT = OpenAI(api_key=st.secrets.openai_api_key)

# Load config
ALLOWED_EMAILS = st.secrets.allowed_emails

NO_LABEL_CODE = "ERROR:NO-LABEL-FOUND"
NO_TYPEFIELD_CODE = "ERROR:NO-TYPEFIELD-FOUND"
DF_KEY = "data_codes"

USER_SYSTEM_PROMPT = "You are a VQA assistant, you help solve visual question-answering tasks provided by the user. Your answer are minimal, providing only the requested information."
USER_PROMPT = f"""
Answer with only the code on the field 'type' in the label. Do not include additional text in your reply.
If the image does not contain a label: answer with '{NO_LABEL_CODE}'.
If the image does not contain a 'TYPE' field: answer with '{NO_TYPEFIELD_CODE}'.

Examples:
> user: <image>
  assistant: A1B-C123-ABC

> user: <image without label>
  assistant: {NO_LABEL_CODE}

> user: <image with a label without the TYPE field>
  assistant: {NO_TYPEFIELD_CODE}
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


def convert_to_excelfile(df: pd.DataFrame) -> io.BytesIO:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Sheet3")
        writer.close()

    return buffer


# Webpages ----------------


def login_page():
    st.title("Pagina di Log-In")
    if st.button("Accedi al tuo account Google ", icon=":material/login:"):
        st.login()


def main():
    if not st.user.is_logged_in:
        login_page()
        st.stop()
    else:
        if st.user.email not in ALLOWED_EMAILS:
            st.error(
                f"Accesso Negato: L'account con email {st.user.email} non è stato autorizzato ad accedere all'applicazione."
            )
            st.stop()

    if DF_KEY not in st.session_state:
        st.session_state[DF_KEY] = pd.DataFrame(columns=["PRODUCT_ID", "TIMESTAMP"])
    df = st.session_state[DF_KEY]

    st.set_page_config(page_title="Annotation App")
    st.title("Extrazione codici OMRON")
    st.write("Questa è un app per l'estrazione automatica del codice di prodotti elettronici mandati da Omron Italia.")

    uploaded_image = st.camera_input("Fai una foto")

    if uploaded_image is not None:
        if st.button("Invia immagine al server."):
            image = Image.open(uploaded_image)

            # Send POST request
            with st.spinner("Stiamo processando l'immagine, per favore attendere..."):
                with tempfile.NamedTemporaryFile(suffix=".jpg") as fp:
                    image.save(fp)
                    response = request_id(CLIENT, fp.name)

            if response == NO_LABEL_CODE:
                st.warning("L'immagine non contiene un'etichetta.")
            elif response == NO_TYPEFIELD_CODE:
                st.warning("L'etichetta nell'immagine non dispone di un campo 'TYPE'.")
            else:
                st.markdown("**PRODUCT-ID:** {response}")

                # Update dataframe
                timestamp = datetime.today().strftime("%Y-%m-%d_%H%M")
                df.loc[len(df)] = (response, timestamp)

        # Show dataframe
        st.markdown("Prodotti scansionati:")
        st.dataframe(df)

        st.download_button(
            label="Scarica il file excel",
            data=convert_to_excelfile(df),
            file_name="product_ids.xlsx",
            mime="application/vnd.ms-excel",
            icon=":material/download:",
        )
    else:
        st.info("Fare una foto per scansionare e processare l'etichetta.")


if __name__ == "__main__":
    main()
