import io
from typing import *
from datetime import datetime

from openai import OpenAI
import streamlit as st
from PIL import Image
import pandas as pd

from idrec.request import request_id, ResponseCodes

# Load secrets data
ALLOWED_EMAILS = st.secrets.allowed_emails
CLIENT = OpenAI(api_key=st.secrets.openai_api_key)

# Session state keys
SSTATE_DF_KEY = "data_codes"
SSTATE_LASTRESPONSE_KEY = "last_product_id"


def convert_to_excelfile(df: pd.DataFrame) -> io.BytesIO:
    """Convert DataFrame df into a string of bytes representing an excel object."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Sheet3")
    return buffer


# User data  in memory DB (each email has a rispective DataFrame)
@st.cache_resource
def get_userdata(user_mail: str) -> pd.DataFrame:
    return pd.DataFrame(columns=["PRODUCT_ID", "TIMESTAMP"])


# Callbacks ---------------
def flag_for_request():
    st.session_state.is_requesting = True


def reset_data():
    df = get_userdata(st.user.email)
    df.drop(df.index, inplace=True)


# Webpages ----------------
def login_page():
    st.title("Pagina di Log-In")
    if st.button("Accedi al tuo account Google ", icon=":material/login:"):
        st.login()


def access_denied_page():
    st.error(
        f"Accesso Negato: L'account con email {st.user.email} non è stato autorizzato ad accedere all'applicazione."
    )


def main_page():

    # User and session data
    df = get_userdata(st.user.email)
    is_requesting = st.session_state.get("is_requesting", False)
    (response, response_code) = st.session_state.get(SSTATE_LASTRESPONSE_KEY, ("", None))

    st.set_page_config(page_title="Annotation App")
    st.title("Estrazione ID-prodotto")
    st.write(
        "Questa è un app per l'estrazione automatica di campi testuali da etichette di spedizioni di prodotti elettronici."
    )
    target_field = st.text_input("Campo da estrarre:", "TYPE")
    uploaded_image = st.camera_input(label="camera", label_visibility="hidden", disabled=is_requesting)
    uploaded_image = st.file_uploader("Upload") if uploaded_image is None else None

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
                response, response_code = request_id(CLIENT, Image.open(uploaded_image), target_field)
                st.session_state.is_requesting = False

            st.session_state[SSTATE_LASTRESPONSE_KEY] = (response, response_code)

            # If no errors: Update dataframe
            if response_code is ResponseCodes.FIELD_FOUND_CODE:
                timestamp = datetime.today().isoformat(timespec="seconds")
                df.loc[len(df)] = (response, timestamp)

            st.rerun()
    else:
        st.info("Fare una foto per scansionare e processare l'etichetta.")

    # Show DATA
    if response_code == ResponseCodes.NO_LABEL_CODE:
        st.warning("L'immagine non contiene un'etichetta.")
    elif response_code == ResponseCodes.NO_FIELD_CODE:
        st.warning("L'etichetta nell'immagine non dispone di un campo 'TYPE'.")
    elif response_code == ResponseCodes.FIELD_FOUND_CODE:
        st.markdown(f"**PRODUCT-ID:** {response}")

    st.markdown("**PRODOTTI SCANSIONATI:**")
    df.sort_values(by="TIMESTAMP", ascending=False, inplace=True)
    tmp_df = st.data_editor(df, hide_index=True)
    for idx in df.index:
        df.loc[idx] = tmp_df.loc[idx]

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


def main():
    if not st.user.is_logged_in:  # Check if the user is already logged
        login_page()
        st.stop()
    elif st.user.email not in ALLOWED_EMAILS:  # Check that the user email is in the provided whitelist
        access_denied_page()
        st.stop()
    else:
        main_page()


if __name__ == "__main__":
    main()
