import streamlit as st

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login():
    if st.button("Log in"):
        st.session_state.logged_in = True
        st.rerun()

def logout():
    if st.button("Log out"):
        st.session_state.logged_in = False
        st.rerun()

login_page = st.Page(login, title="Log in", icon=":material/login:")
logout_page = st.Page(logout, title="Log out", icon=":material/logout:")

chat_page = st.Page("page/chat.py", title="Chat Bot", icon=":material/add_circle:")
qa_page = st.Page("page/qa.py", title="QA Section", icon=":material/delete:")

if st.session_state.logged_in:
    pg = st.navigation(
        {
            "Account": [logout_page],
            "Tools": [chat_page, qa_page],
        }
    )
else:
    pg = st.navigation([login_page])

pg.run()