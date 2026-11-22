import os
import json
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables (works locally with .env and on Streamlit Cloud via Secrets)
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")

st.set_page_config(page_title="Campus Maintenance AI", page_icon="🏫", layout="wide")

# Initialize Gemini client
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
MODEL_ID = "gemini-2.5-flash"

# Store logged complaints in session state so the Insights tab can analyze them
if "complaints" not in st.session_state:
    st.session_state.complaints = []

st.title("🏫 Campus Maintenance Inspection AI")

if not client:
    st.error("⚠️ GEMINI_API_KEY is not configured. Add it to your `.env` file or Streamlit Secrets.")
    st.stop()

tab1, tab2 = st.tabs(["📸 Inspect Facility Defect", "📊 Campus Estate Insights"])

# --- TAB 1: Replaces /api/analyze-image ---
with tab1:
    st.subheader("Report & Analyze Infrastructure Defect")
    
    uploaded_file = st.file_uploader("Upload a photo of the issue", type=["jpg", "jpeg", "png", "webp"])
    user_hint = st.text_input("Additional context (e.g., Block B, 2nd Floor Lab, leaking since morning)")

    if uploaded_file is not None:
        st.image(uploaded_file, caption="Uploaded Photo", width=400)

        if st.button("Analyze Issue", type="primary"):
            with st.spinner("Inspecting image with Gemini AI..."):
                prompt = (
                    "You are a campus maintenance inspection AI for an Indian college campus. "
                    "Analyze this photograph and identify the visible facility/infrastructure defect. "
                    f"Additional user context: {user_hint}. "
                    "Return strict JSON with keys: "
                    "detectedIssue (string), "
                    "category (one of: Electrical, Plumbing, Furniture, Cleanliness, Laboratory Equipment, Other), "
                    "suggestedPriority (one of: Low, Medium, High, Urgent), "
                    "priorityReason (string), "
                    "description (clear 2-sentence formal complaint description), "
                    "confidence (number between 0 and 1)."
                )

                try:
                    image_bytes = uploaded_file.getvalue()
                    mime_type = uploaded_file.type or "image/jpeg"

                    response = client.models.generate_content(
                        model=MODEL_ID,
                        contents=[
                            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                            prompt,
                        ],
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json"
                        ),
                    )
                    result = json.loads(response.text)

                    # Save ticket to session history
                    st.session_state.complaints.append(result)

                    # Display formatted results
                    st.success("Analysis Complete!")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Category", result.get("category", "N/A"))
                    col2.metric("Priority", result.get("suggestedPriority", "N/A"))
                    col3.metric("AI Confidence", f"{int(result.get('confidence', 0) * 100)}%")

                    st.markdown(f"**Detected Issue:** {result.get('detectedIssue')}")
                    st.markdown(f"**Priority Reason:** {result.get('priorityReason')}")
                    st.info(f"**Formal Complaint:** {result.get('description')}")

                except Exception as exc:
                    st.error(f"Error analyzing image: {exc}")

# --- TAB 2: Replaces /api/campus-insights ---
with tab2:
    st.subheader("Campus Administrator Insights")
    st.write(f"Logged complaints in current session: **{len(st.session_state.complaints)}**")

    if st.session_state.complaints:
        with st.expander("View Logged Tickets"):
            st.json(st.session_state.complaints)

        if st.button("Generate Estate Insights"):
            with st.spinner("Analyzing campus trends..."):
                prompt = (
                    "Analyze these campus maintenance tickets and provide concise actionable insights "
                    "for the campus estate administrator. Return strict JSON with keys: "
                    "hotspots (list of strings), recurringPatterns (list of strings), "
                    "preventiveActions (list of strings), executiveSummary (string). "
                    f"Complaints data: {json.dumps(st.session_state.complaints[:40])}"
                )

                try:
                    response = client.models.generate_content(
                        model=MODEL_ID,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json"
                        ),
                    )
                    insights = json.loads(response.text)

                    st.markdown("### Executive Summary")
                    st.write(insights.get("executiveSummary"))

                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.markdown("#### 🔥 Hotspots")
                        for item in insights.get("hotspots", []):
                            st.write(f"- {item}")
                    with c2:
                        st.markdown("#### 🔄 Recurring Patterns")
                        for item in insights.get("recurringPatterns", []):
                            st.write(f"- {item}")
                    with c3:
                        st.markdown("#### 🛠️ Preventive Actions")
                        for item in insights.get("preventiveActions", []):
                            st.write(f"- {item}")

                except Exception as exc:
                    st.error(f"Error generating insights: {exc}")
    else:
        st.info("Analyze at least one facility photo in the first tab to generate insights.")
