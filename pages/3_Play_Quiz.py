# 🎮 pages/3_Play_Quiz.py — India Mini-Quiz with Neon DB integration + Balloons on Full Score

import os
import streamlit as st
import pandas as pd
from sqlalchemy import text
from db_connect import get_engine

# ---------------------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------------------
st.set_page_config(page_title="Play Quiz", page_icon="🎮", layout="wide")
st.title("🎮 India Mini-Quiz")
st.write("Answer 8 fun questions and see your score instantly!")

# ---------------------------------------------------------------
# QUIZ QUESTIONS & ANSWERS
# ---------------------------------------------------------------
ANSWERS = {
    "q1": "New Delhi",
    "q2": "Spicy",
    "q3": "Holi",
    "q4": "With Bread (like naan or roti)",
    "q5": "Himachal Pradesh",
    "q6": "Rupee",
    "q7": "Sari",
    "q8": "Agra"
}

# ---------------------------------------------------------------
# DB CONNECTION
# ---------------------------------------------------------------
try:
    engine = get_engine()
except Exception as e:
    st.error(f"❌ Database connection failed: {e}")
    st.stop()

# ---------------------------------------------------------------
# QUIZ FORM
# ---------------------------------------------------------------
with st.form("quiz_form"):
    name = st.text_input("Your Name *")
    st.divider()

    q1 = st.radio("What is the capital city of India?", ["New Delhi", "Mumbai", "Goa", "Pune"], index=None)
    q2 = st.radio("🥘👨‍🍳🌶️🥵 What word best describes Indian food?", ["Spicy", "Sweet", "Cold"], index=None)
    q3 = st.radio("🌈🎨 Which Indian festival is known as the Festival of Colors?", ["Diwali", "Holi", "Eid"], index=None)
    q4 = st.radio("🍞 + 🍛 = ❓What is a popular way of eating Indian curry?", ["With Bread (like naan or roti)", "With a spoon"], index=None)
    q5 = st.radio("🚩🌄🧗‍♂️Which region in India is famous for the Himalayas?", ["Kerala", "Himachal Pradesh", "Gujarat"], index=None)
    q6 = st.radio("💵💰🪙Which of these is the Indian currency?", ["Rupee", "Yen", "Peso"], index=None)
    q7 = st.radio("🥻🧵🌺 What is a traditional Indian dress for women called?", ["Sari", "Kimono", "Poncho"], index=None)
    q8 = st.radio("🏰 Which city is home to the famous Taj Mahal?", ["Agra", "Delhi", "Jaipur"], index=None)

    submit = st.form_submit_button("Submit")

# ---------------------------------------------------------------
# FORM LOGIC
# ---------------------------------------------------------------
if submit:
    if not name:
        st.error("⚠️ Please enter your name before submitting.")
    else:
        selections = [q1, q2, q3, q4, q5, q6, q7, q8]
        correct = sum(a == b for a, b in zip(selections, ANSWERS.values()))

        # 🎉 Show score
        st.success(f"🎉 {name}, you scored **{correct}/8**!")

        # 🎈 Show balloons if all answers are correct
        if correct == 8:
            st.balloons()

        # ❌ Show incorrect answers (if any)
        wrong = [q for q, (a, b) in zip(ANSWERS.keys(), zip(selections, ANSWERS.values())) if a != b]
        if wrong:
            st.write("❌ Incorrect answers:")
            for q in wrong:
                st.markdown(f"- **{q.upper()}** → Correct answer: **{ANSWERS[q]}**")

        # ✅ Save to Neon DB
        try:
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        CREATE TABLE IF NOT EXISTS quiz_results (
                            id SERIAL PRIMARY KEY,
                            name TEXT,
                            score INT,
                            date_submitted TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                )
                conn.execute(
                    text("""
                        INSERT INTO quiz_results (name, score)
                        VALUES (:name, :score)
                    """),
                    {"name": name, "score": correct}
                )
            st.info("✅ Your response has been saved successfully!")
        except Exception as e:
            st.error(f"⚠️ Error saving your response: {e}")

# ---------------------------------------------------------------
# LEADERBOARD
# ---------------------------------------------------------------
st.markdown("---")
st.header("🏆 Leaderboard")

try:
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT name, score, date_submitted FROM quiz_results ORDER BY score DESC, date_submitted ASC")
        ).fetchall()

        if rows:
            df = pd.DataFrame(rows, columns=["NAME", "SCORE OUT OF 8", "DATE SUBMITTED"])
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Optional: download leaderboard
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download Leaderboard", csv, "quiz_leaderboard.csv", "text/csv")

        else:
            st.info("No quiz results yet.")
except Exception as e:
    st.warning(f"⚠️ Could not load leaderboard: {e}")
