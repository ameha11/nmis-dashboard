import streamlit as st

def login():
    st.title("🔐 Login to NMIS Dashboard")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        users = st.secrets["users"]

        if username in users and password == users[username]["password"]:
            st.session_state["user"] = username
            st.session_state["role"] = users[username]["role"]
            st.session_state["logged_in"] = True
            st.rerun()
        else:
            st.error("Incorrect username or password")

    st.stop()
