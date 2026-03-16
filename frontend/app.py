import streamlit as st
import requests

st.title("Document Processing")

files = st.file_uploader(
    "Upload documents",
    accept_multiple_files=True
)

if st.button("Upload"):

    if files:

        response = requests.post(
            "http://localhost:8000/upload",
            files=[("files", f) for f in files]
        )

        st.write(response.json())