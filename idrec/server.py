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
LAST_RESPONSE_KEY = "last_product_id"

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
        result = client.files.create(file=file_content, purpose="vision")
        return result.id


def request_id(client: OpenAI, image: Image) -> str:

    with tempfile.NamedTemporaryFile(suffix=".jpg") as fp:
        image.save(fp)
        # image_data = client.files.create(file=fp, purpose="vision")
        image_data = create_file(client, fp.name)
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


def convert_to_excelfile(df: pd.DataFrame) -> io.BytesIO:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Sheet3")
    return buffer


# Webpages ----------------


def flag_for_request():
    st.session_state.is_requesting = True


def reset_data():
    st.session_state[DF_KEY] = pd.DataFrame(columns=["PRODUCT_ID", "TIMESTAMP"])


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

    # Initialize session data
    if DF_KEY not in st.session_state:
        st.session_state[DF_KEY] = pd.DataFrame(columns=["PRODUCT_ID", "TIMESTAMP"])
        st.session_state[LAST_RESPONSE_KEY] = "-"

    # Get session data
    is_requesting = st.session_state.get("is_requesting", False)
    df = st.session_state[DF_KEY]

    st.set_page_config(page_title="Annotation App")
    st.title("Extrazione codici OMRON")
    st.write("Questa è un app per l'estrazione automatica del codice di prodotti elettronici mandati da Omron Italia.")

    uploaded_image = st.camera_input(label="camera", label_visibility="hidden", disabled=is_requesting)

    # Process image
    if uploaded_image is not None:
        if st.button(
            "Invia immagine al server.",
            width="stretch",
            type="primary",
            on_click=flag_for_request,
            disabled=is_requesting,
        ):
            with st.spinner("Stiamo processando l'immagine, per favore attendere..."):
                response = request_id(CLIENT, Image.open(uploaded_image))
                st.session_state.is_requesting = False

            st.session_state[LAST_RESPONSE_KEY] = response

            # If no errors: Update dataframe
            if response not in [NO_LABEL_CODE, NO_TYPEFIELD_CODE]:
                timestamp = datetime.today().strftime("%Y-%m-%d_%H%M")
                df.loc[len(df)] = (response, timestamp)

            st.rerun()

    else:
        st.info("Fare una foto per scansionare e processare l'etichetta.")

    # Show DATA
    response = st.session_state[LAST_RESPONSE_KEY]
    if response == NO_LABEL_CODE:
        st.warning("L'immagine non contiene un'etichetta.")
    elif response == NO_TYPEFIELD_CODE:
        st.warning("L'etichetta nell'immagine non dispone di un campo 'TYPE'.")
    else:
        st.markdown(f"**PRODUCT-ID:** {st.session_state[LAST_RESPONSE_KEY]}")
    st.markdown("**PRODOTTI SCANSIONATI:**")
    st.session_state[DF_KEY] = st.data_editor(df, hide_index=True)

    c1, c2 = st.columns([0.7, 0.3])
    with c1:
        st.download_button(
            label="Scarica il file excel",
            data=convert_to_excelfile(df),
            file_name="product_ids.xlsx",
            mime="application/vnd.ms-excel",
            icon=":material/download:",
            width="stretch",
        )

    with c2:
        st.button("Azzera dati", icon=":material/delete:", on_click=reset_data, type="primary", width="stretch")


if __name__ == "__main__":
    main()
