import streamlit as st
import requests
import pandas as pd
import os
import json
from pymongo import MongoClient

# --- CONFIG ---
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017/hackathon")

st.set_page_config(
    page_title="Document Processing Analytics",
    page_icon="📄",
    layout="wide",
)

# --- DB HELPERS ---
@st.cache_resource
def get_db():
    client = MongoClient(MONGO_URI)
    return client.hackathon

db = get_db()

# --- APP ---
st.title("🚀 Document Processing Dashboard")
st.markdown("---")

tabs = st.tabs(["📊 Overview", "📁 Data Lake Explorer", "🛡️ Validation & Fraud", "📤 Upload Test"])

with tabs[0]:
    st.header("System Snapshot")
    col1, col2, col3, col4 = st.columns(4)

    # Stats from MongoDB
    try:
        total_docs = db.documents.count_documents({})
        raw_count = db.documents.count_documents({"status": "raw"})
        clean_count = db.documents.count_documents({"status": "clean"})
        curated_count = db.documents.count_documents({"status": "curated"})
        anomalies_count = db.anomalies.count_documents({})

        col1.metric("Total Documents", total_docs)
        col2.metric("Raw (Bronze)", raw_count)
        col3.metric("Clean (Silver)", clean_count)
        col4.metric("Curated (Gold)", curated_count)

        st.subheader("Document Types Distribution")
        docs_list = list(db.documents.find({}, {"predicted_type": 1, "_id": 0}))
        if docs_list:
            df_types = pd.DataFrame(docs_list)
            st.bar_chart(df_types['predicted_type'].value_counts())
        else:
            st.info("No documents yet.")

    except Exception as e:
        st.error(f"Could not connect to database: {e}")

with tabs[1]:
    st.header("Data Lake Browsing")
    layer = st.selectbox("Select Layer", ["Raw", "Clean", "Curated"])
    base_data = "data"
    layer_dir = f"{base_data}/{layer.lower()}"
    
    if os.path.exists(layer_dir):
        files = os.listdir(layer_dir)
        if files:
            selected_file = st.selectbox("Select File", files)
            file_path = os.path.join(layer_dir, selected_file)
            
            with st.expander(f"Preview: {selected_file}"):
                if selected_file.endswith('.json'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        st.json(json.load(f))
                elif selected_file.endswith('.txt'):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        st.text(f.read())
                else:
                    st.write(f"Binary file: {selected_file}")
        else:
            st.info(f"No files in the '{layer}' layer yet.")
    else:
        st.warning(f"Directory {layer_dir} not found. (Current CWD: {os.getcwd()})")


with tabs[2]:
    st.header("Validation Anomalies")
    anomalies = list(db.anomalies.find().sort("detected_at", -1))
    
    if anomalies:
        display_data = []
        for a in anomalies:
            doc_ids = a.get("document_ids", [])
            filenames = []
            if doc_ids:
                docs = list(db.documents.find({"document_id": {"$in": doc_ids}}, {"filename": 1}))
                filenames = [d["filename"] for d in docs]
            
            display_data.append({
                "Date": a.get("detected_at"),
                "Files": ", ".join(filenames) if filenames else "N/A",
                "Severity": a.get("severity", "medium").upper(),
                "Code": a.get("rule_code"),
                "Message": a.get("message")
            })
            
        df_anomalies = pd.DataFrame(display_data)
        st.dataframe(df_anomalies, width="stretch", hide_index=True)
    else:
        st.success("No anomalies detected! System is healthy.")

with tabs[3]:
    st.header("📤 Batch Document Processing")
    st.info("Upload multiple invoices, quotes, or ID documents for automated extraction and validation.")
    
    uploaded_files = st.file_uploader(
        "Drop documents here", 
        type=['pdf', 'jpg', 'png', 'jpeg', 'webp'], 
        accept_multiple_files=True,
        help="Supported formats: PDF, JPG, PNG, WEBP"
    )
    
    if uploaded_files:
        st.write(f"📂 **{len(uploaded_files)}** files ready for processing.")
        
        if st.button("🚀 Start Pipeline", width="stretch"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Construct multi-file payload for FastAPI
                files_payload = [
                    ("files", (f.name, f.getvalue(), f.type)) 
                    for f in uploaded_files
                ]
                
                status_text.text("Sending to processing engine...")
                progress_bar.progress(30)
                
                resp = requests.post(f"{BACKEND_URL}/upload", files=files_payload)
                
                progress_bar.progress(100)
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])
                    alerts = data.get("cross_document_alerts", [])
                    
                    st.success(f"✅ Finished! {len(results)} files processed.")
                    
                    # Display summary in columns
                    cols = st.columns(min(len(results), 3))
                    for idx, res in enumerate(results):
                        with cols[idx % 3]:
                            with st.container(border=True):
                                st.write(f"📄 **{res['filename']}**")
                                st.caption(f"Status: {res['status']}")
                                st.write(f"Type: `{res.get('document_type', 'unknown')}`")
                                if res.get('validation'):
                                    score = res['validation'].get('score', 0)
                                    st.progress(score / 100, text=f"Score: {score}%")
                    
                    if alerts:
                        st.warning(f"⚠️ {len(alerts)} cross-document inconsistencies detected!")
                        with st.expander("View Alerts"):
                            st.json(alerts)
                            
                    with st.expander("Full JSON Response"):
                        st.json(data)
                else:
                    st.error(f"❌ Backend Error ({resp.status_code}): {resp.text}")
                    
            except Exception as e:
                st.error(f"☢️ System Failure: {e}")
            finally:
                status_text.empty()

# Sidebar
st.sidebar.title("Hackathon Settings")
st.sidebar.info("Medallion Architecture: Raw → Clean → Curated")
if st.sidebar.button("Refresh Dashboard"):
    st.rerun()

