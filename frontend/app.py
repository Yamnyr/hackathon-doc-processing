import streamlit as st
import requests
import os

backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

st.title("Document Processing")

files = st.file_uploader(
    "Upload documents",
    accept_multiple_files=True
)

if st.button("Upload"):

    if files:

        response = requests.post(
            f"{backend_url}/upload",
            files=[("files", f) for f in files]
        )

        st.write(response.json())