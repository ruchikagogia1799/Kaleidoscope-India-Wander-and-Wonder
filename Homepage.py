# Homepage.py — Kaleidoscope India: Animated GIF + Functional Explore Button
# Run: streamlit run Homepage.py

import os
import base64
import streamlit as st

st.set_page_config(page_title="Kaleidoscope India", page_icon="🌏", layout="wide")

# ---------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------
st.title("🌍 Welcome to Kaleidoscope India - Wander & Wonder")
st.caption("Discover India's vibrant attractions, local cuisine, and hidden gems — all in one place!")

# ---------------------------------------------------------------
# HERO SECTION — PLAYING GIF + TEXT SIDE BY SIDE
# ---------------------------------------------------------------
gif_path = "ind.gif"

col1, col2 = st.columns([1, 2], gap="large")

with col1:
    if os.path.exists(gif_path):
        with open(gif_path, "rb") as f:
            gif_base64 = base64.b64encode(f.read()).decode()

        # ✅ Larger GIF (400 px max width) that actually scales
        gif_html = f"""
        <div style='text-align:center;'>
            <img src='data:image/gif;base64,{gif_base64}'
                 style='max-width:400px; width:100%; border-radius:14px;
                        box-shadow:0 2px 8px rgba(0,0,0,0.1);' alt='Discover India'>
            <p style='font-size:0.9rem; color:gray;'>Discover India – Wander & Wonder</p>
        </div>
        """
        st.markdown(gif_html, unsafe_allow_html=True)
    else:
        st.warning("⚠️ Couldn't find 'ind.gif'. Please place it in the same folder as this script.")

with col2:
    st.markdown("""
    **Features:**
    - 🏰 Explore attractions with ratings, images & local cuisine suggestions  
    - 🍛 Discover regional dishes  
    - 🧭 Filter by state, city, and attraction type  
    - 🎮 Play a fun Indian quiz  
    - 💬 Share feedback and connect  
    """)

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------------
# ACTION BUTTON — CENTERED + STREAMLIT NAVIGATION
# ---------------------------------------------------------------
st.markdown("---")
col_btn = st.columns([1, 1,1])
with col_btn[1]:  # center column
    if st.button("🚀 Start Exploring →", type="primary", width='stretch'):
        st.switch_page("pages/2_Explore.py")  # ✅ works in multipage Streamlit apps

# ---------------------------------------------------------------
# FOOTER
# ---------------------------------------------------------------
st.markdown("---")
st.caption("🧭 Built with ❤️ using Streamlit • Explore, Discover, Taste, and Travel India")
