import streamlit as st
import sqlite3
import json
import google.generativeai as genai
import os
# ==========================================
# 1. CONFIGURE GEMINI API
# ==========================================

genai.configure(api_key=os.getenv("AIzaSyA4P7DtKYiN8rUE5lws-ehj4l9UGSfL1Us"))

model = genai.GenerativeModel("gemini-1.5-pro")

# ==========================================
# 2. DATABASE SETUP (SQLite)
# ==========================================
def init_db():
    conn = sqlite3.connect('hackathon_db.sqlite')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS employees 
                 (id INTEGER PRIMARY KEY, name TEXT, leave_balance INTEGER)''')

    c.execute('''CREATE TABLE IF NOT EXISTS tickets 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, emp_id INTEGER, dept TEXT, desc TEXT, status TEXT)''')

    # Insert mock data
    c.execute("SELECT * FROM employees WHERE id=1001")
    if not c.fetchone():
        c.execute("INSERT INTO employees VALUES (1001, 'Sarah', 2)")
        conn.commit()

    conn.close()

# ==========================================
# 3. DATABASE FUNCTIONS (TOOLS)
# ==========================================
def get_leave_balance(emp_id):
    conn = sqlite3.connect('hackathon_db.sqlite')
    c = conn.cursor()
    c.execute("SELECT leave_balance FROM employees WHERE id=?", (emp_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

def apply_leave(emp_id, days):
    conn = sqlite3.connect('hackathon_db.sqlite')
    c = conn.cursor()

    c.execute("SELECT leave_balance FROM employees WHERE id=?", (emp_id,))
    current = c.fetchone()[0]

    if current >= days:
        new_balance = current - days
        c.execute("UPDATE employees SET leave_balance=? WHERE id=?", (new_balance, emp_id))
        conn.commit()
        conn.close()
        return f"✅ Leave approved. {days} days deducted. Remaining: {new_balance}"
    else:
        conn.close()
        return f"❌ Not enough leave. You have {current} days only."

def create_ticket(emp_id, dept, desc):
    conn = sqlite3.connect('hackathon_db.sqlite')
    c = conn.cursor()

    c.execute("INSERT INTO tickets (emp_id, dept, desc, status) VALUES (?, ?, ?, 'Open')",
              (emp_id, dept, desc))
    conn.commit()
    ticket_id = c.lastrowid
    conn.close()

    return f"🎫 Ticket #{ticket_id} created for {dept}"

# ==========================================
# 4. AGENT LOGIC (SIMULATED WORKFLOW)
# ==========================================
def run_agent(user_input):
    emp_id = 1001

    # Step 1: Ask Gemini to classify intent
    prompt = f"""
    Classify the user request into one of these:
    - leave_request
    - problem_report
    - general

    Also extract:
    - number of days (if leave)
    - department (IT, HR, Facilities if problem)

    User: {user_input}

    Respond ONLY in JSON format like:
    {{
        "intent": "...",
        "days": 0,
        "department": "...",
        "description": "..."
    }}
    """

    response = model.generate_content(prompt)
    
    try:
        data = json.loads(response.text)
    except:
        return "⚠️ AI parsing error. Try again."

    intent = data.get("intent")

    # Step 2: Workflow execution
    if intent == "leave_request":
        days = data.get("days")

        if not days or days == 0:
            return "❓ How many days of leave do you want?"

        balance = get_leave_balance(emp_id)

        if balance < days:
            return f"❌ You only have {balance} days left."

        return apply_leave(emp_id, days)

    elif intent == "problem_report":
        dept = data.get("department", "IT")
        desc = data.get("description", user_input)
        return create_ticket(emp_id, dept, desc)

    else:
        # fallback chatbot
        reply = model.generate_content(user_input)
        return reply.text

# ==========================================
# 5. STREAMLIT UI
# ==========================================
st.set_page_config(page_title="AI Workflow Portal", page_icon="🤖")
init_db()

st.title("🤖 Gemini AI Workflow Automation")
st.markdown("---")

st.sidebar.success("Logged in as Sarah (ID: 1001)")

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User input
if prompt := st.chat_input("Type your request..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("AI thinking..."):
        response = run_agent(prompt)

    st.chat_message("assistant").markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
