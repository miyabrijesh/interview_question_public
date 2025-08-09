
import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import random

DB = "interview_questions.db"

@st.cache_resource
def get_conn():
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company TEXT,
        role TEXT,
        topic TEXT,
        difficulty TEXT,
        question TEXT NOT NULL,
        answer TEXT,
        date_added TEXT,
        notes TEXT
    )
    """)
    return conn

def fetch_df(conn, where_clause="", params=()):
    return pd.read_sql_query(f"SELECT * FROM questions {where_clause} ORDER BY id DESC", conn, params=params)

st.set_page_config(page_title="Interview Question Organizer", page_icon="🗂️", layout="wide")
st.title("Interview Question Organizer")

conn = get_conn()

with st.expander("➕ Add Question", expanded=True):
    with st.form("add_q", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            company = st.text_input("Company", placeholder="Google")
            topic = st.text_input("Topic/Tag", placeholder="Arrays / DBMS / OS / ML / System Design")
        with c2:
            role = st.text_input("Role", placeholder="SDE / Data Analyst")
            difficulty = st.selectbox("Difficulty", ["Easy","Medium","Hard"], index=0)
        with c3:
            date_added = st.date_input("Date", value=date.today())
        question = st.text_area("Question*", placeholder="Describe the difference between processes and threads...")
        answer = st.text_area("Answer / Approach", placeholder="Key points, hints, steps...")
        notes = st.text_area("Notes", placeholder="Source, link, round, etc.")
        submitted = st.form_submit_button("Add")
        if submitted:
            if not question.strip():
                st.error("Question is required.")
            else:
                conn.execute(
                    "INSERT INTO questions (company, role, topic, difficulty, question, answer, date_added, notes) VALUES (?,?,?,?,?,?,?,?)",
                    (company or None, role or None, topic or None, difficulty, question.strip(), answer or None, str(date_added), notes or None)
                )
                conn.commit()
                st.success("Saved!")

st.markdown("---")

# Filters
with st.sidebar:
    st.markdown("### Filters")
    topics = [r[0] for r in conn.execute("SELECT DISTINCT COALESCE(topic,'') FROM questions").fetchall() if r[0]]
    roles = [r[0] for r in conn.execute("SELECT DISTINCT COALESCE(role,'') FROM questions").fetchall() if r[0]]
    companies = [r[0] for r in conn.execute("SELECT DISTINCT COALESCE(company,'') FROM questions").fetchall() if r[0]]
    topic_f = st.multiselect("Topic", topics, default=[])
    role_f = st.multiselect("Role", roles, default=[])
    company_f = st.multiselect("Company", companies, default=[])
    search = st.text_input("Search text", placeholder="binary tree, normalization...")

where = []
params = []
if topic_f:
    where.append(f"topic IN ({','.join(['?']*len(topic_f))})")
    params.extend(topic_f)
if role_f:
    where.append(f"role IN ({','.join(['?']*len(role_f))})")
    params.extend(role_f)
if company_f:
    where.append(f"company IN ({','.join(['?']*len(company_f))})")
    params.extend(company_f)
if search:
    where.append("(question LIKE ? OR answer LIKE ? OR notes LIKE ?)")
    params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

where_clause = "WHERE " + " AND ".join(where) if where else ""

df = fetch_df(conn, where_clause, tuple(params))
st.subheader("Questions")
st.dataframe(df, use_container_width=True, hide_index=True)

with st.expander("✏️ Edit / Delete"):
    if df.empty:
        st.info("No questions yet.")
    else:
        ids = df["id"].tolist()
        selected_id = st.selectbox("Select ID", ids, format_func=lambda x: f"#{x} | {df[df['id']==x]['topic'].values[0]} — {df[df['id']==x]['question'].values[0][:40]}...")
        row = df[df["id"]==selected_id].iloc[0]
        with st.form("edit_q"):
            c1, c2, c3 = st.columns(3)
            with c1:
                company = st.text_input("Company", value=row["company"] or "")
                topic = st.text_input("Topic/Tag", value=row["topic"] or "")
            with c2:
                role = st.text_input("Role", value=row["role"] or "")
                difficulty = st.selectbox("Difficulty", ["Easy","Medium","Hard"], index=["Easy","Medium","Hard"].index(row["difficulty"] or "Easy"))
            with c3:
                date_added = st.text_input("Date", value=row["date_added"] or "")
            question = st.text_area("Question*", value=row["question"] or "")
            answer = st.text_area("Answer / Approach", value=row["answer"] or "")
            notes = st.text_area("Notes", value=row["notes"] or "")
            c_edit, c_del = st.columns(2)
            with c_edit:
                update = st.form_submit_button("Update")
            with c_del:
                delete = st.form_submit_button("Delete", type="secondary")
        if update:
            conn.execute("""
                UPDATE questions
                SET company=?, role=?, topic=?, difficulty=?, question=?, answer=?, date_added=?, notes=?
                WHERE id=?
            """, (company or None, role or None, topic or None, difficulty, question.strip(), answer or None, date_added or None, notes or None, int(selected_id)))
            conn.commit()
            st.success("Updated!")
        if delete:
            conn.execute("DELETE FROM questions WHERE id=?", (int(selected_id),))
            conn.commit()
            st.warning("Deleted.")

st.markdown("---")
c1, c2, c3 = st.columns(3)
with c1:
    if not df.empty and st.button("⬇️ Export CSV"):
        st.download_button("Download questions.csv", df.to_csv(index=False).encode("utf-8"), file_name="questions.csv", mime="text/csv")
with c2:
    st.write("")
with c3:
    st.markdown("### Quiz Mode")
    if not df.empty:
        if st.button("Start Quiz (random)"):
            row = df.sample(1).iloc[0]
            st.write(f"**Q:** {row['question']}")
            with st.expander("Show Answer"):
                st.write(row['answer'] or '_No answer saved yet_')
