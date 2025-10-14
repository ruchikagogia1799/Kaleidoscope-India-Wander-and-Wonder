import streamlit as st, urllib.parse

st.set_page_config(page_title="Feedback", page_icon="💬", layout="wide")

CONTACT_EMAIL = "ruchikagogia17@gmail.com"
INSTAGRAM_URL = "https://www.instagram.com/wanderlust.ruchika"

st.title("💌 Feedback & Queries")

st.write("Found an issue or have a feature idea? Send a quick message below — your feedback helps improve the app!")

with st.form("feedback_form"):
    name = st.text_input("Your name", "")
    email = st.text_input("Your email", "")
    subject = st.text_input("Subject", "Feedback for Kaleidoscope India")
    message = st.text_area("Your message", height=150)
    send = st.form_submit_button("Open Email")

if send:
    body = f"Name: {name}\nEmail: {email}\n\n{message}"
    mailto = f"mailto:{CONTACT_EMAIL}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
    st.link_button("📩 Click to Send Email", mailto, width='stretch')
    st.success("If your email app didn’t open, copy the address below.")

st.divider()
st.markdown(f"📧 **Email:** [{CONTACT_EMAIL}](mailto:{CONTACT_EMAIL})")
st.markdown(f"📸 **Instagram:** [wanderlust.ruchika]({INSTAGRAM_URL})")
