import streamlit as st
from dotenv import load_dotenv
import requests
import time

st.set_page_config(
    page_title="Local RAG Chatbot",
    layout="wide",
    initial_sidebar_state="expanded"
)

STRINGS = {
    "en": {
        "status_label": "Status",
        "status_completed": "Completed",
        "lang_label": "Language",
        "model_label": "Choose Model",
        "add_docs_label": "Add Documents",
        "upload_btn": "Upload",
        "reset_btn": "Reset",
        "chat_header": "Chatbot",
        "chat_placeholder": "Enter your message",
        "hide_setting_btn": "Hide Setting", 
        "undo_btn": "Undo",
        "clear_btn": "Clear",
        "reset_chat_btn": "Reset",
        "ollama": "Ollama",
        "gemini": "Gemini",
        "en": "English",
        "vn": "Vietnamese",
        "upload_file_status": "Uploaded file:",
        "upload_and_process": "Uploading and processing PDF...",
        "upload_success": "Uploaded! Pages processed: {pages}",
        "upload_failed": "Failed to upload PDF.",
        "thinking": "Thinking...",
        "error_backend": "Error from backend.",
        "no_answer": "No answer.",
        "nav_chat": "Chat",
        "nav_qa": "QA Section",
        "qa_section_title": "QA Section",
        "qa_section_description": "This section is dedicated to specific Question-Answering functionalities. More features coming soon!",
        "qa_example_question": "Example QA Question:",
        "qa_example_answer": "This is an example answer from the QA section.",
        "qa_input_placeholder": "Ask a specific question here...",
        "qa_submit_button": "Get Answer",
        "send_button": "Send",
    },
    "vn": {
        "status_label": "Trạng thái",
        "status_completed": "Hoàn thành",
        "lang_label": "Ngôn ngữ",
        "model_label": "Chọn Mô hình",
        "add_docs_label": "Thêm tài liệu",
        "upload_btn": "Tải lên",
        "reset_btn": "Đặt lại",
        "chat_header": "Chatbot",
        "chat_placeholder": "Nhập tin nhắn của bạn",
        "hide_setting_btn": "Ẩn cài đặt",
        "undo_btn": "Hoàn tác",
        "clear_btn": "Xóa",
        "reset_chat_btn": "Đặt lại",
        "ollama": "Ollama",
        "gemini": "Gemini",
        "en": "Tiếng Anh",
        "vn": "Tiếng Việt",
        "upload_file_status": "Tệp đã tải lên:",
        "upload_and_process": "Đang tải lên và xử lý PDF...",
        "upload_success": "Đã tải lên! Số trang đã xử lý: {pages}",
        "upload_failed": "Tải lên PDF thất bại.",
        "thinking": "Đang suy nghĩ...",
        "error_backend": "Lỗi từ backend.",
        "no_answer": "Không có câu trả lời.",
        "nav_chat": "Trò chuyện",
        "nav_qa": "Phần Hỏi & Đáp",
        "qa_section_title": "Phần Hỏi & Đáp",
        "qa_section_description": "Phần này dành riêng cho các chức năng Hỏi & Đáp cụ thể. Nhiều tính năng khác sẽ sớm ra mắt!",
        "qa_example_question": "Câu hỏi ví dụ:",
        "qa_example_answer": "Đây là câu trả lời ví dụ từ phần Hỏi & Đáp.",
        "qa_input_placeholder": "Đặt câu hỏi cụ thể ở đây...",
        "qa_submit_button": "Nhận câu trả lời",
        "send_button": "Gửi",
    }
}

BACKEND_URL = "http://localhost:8000"

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = None
if "selected_lang" not in st.session_state:
    st.session_state.selected_lang = "en"
if "selected_model" not in st.session_state:
    st.session_state.selected_model = "ollama"
if "settings_visible" not in st.session_state:
    st.session_state.settings_visible = True
if "current_page" not in st.session_state:
    st.session_state.current_page = "Chat"


def add_message(role, content):
    st.session_state.chat_history.append({
        "role": role,
        "content": content,
        "timestamp": time.time()
    })

def clear_chat():
    st.session_state.chat_history = []

def display_chat_messages(strings):
    # This loop renders all previous messages
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # This handles the initial assistant message if no chat history
    if not st.session_state.chat_history:
        with st.chat_message("assistant"):
            st.write("Hello! How can I help you with your document today?")


def main():
    load_dotenv()

    # --- Sidebar ---
    with st.sidebar:
        # Navigation
        st.write("### Navigation") 
        page_options = {
            "Chat": STRINGS[st.session_state.selected_lang]["nav_chat"],
            "QA Section": STRINGS[st.session_state.selected_lang]["nav_qa"]
        }
        page = st.radio(
            "",
            options=list(page_options.keys()),
            format_func=lambda x: page_options[x],
            index=0 if st.session_state.current_page == "Chat" else 1,
            key="navigation_radio"
        )
        if page != st.session_state.current_page:
            st.session_state.current_page = page
            st.rerun()

        strings = STRINGS[st.session_state.selected_lang]

        st.markdown("---")

        # st.subheader(strings["status_label"])
        # st.success(strings["status_completed"])
        # st.markdown("---")

        st.subheader(strings["lang_label"])
        lang_options = {"en": strings["en"], "vn": strings["vn"]}
        selected_lang_display = st.radio(
            "",
            options=list(lang_options.keys()),
            format_func=lambda x: lang_options[x],
            index=0 if st.session_state.selected_lang == "en" else 1,
            key="lang_selector"
        )
        if selected_lang_display != st.session_state.selected_lang:
            st.session_state.selected_lang = selected_lang_display
            st.rerun()
            
        strings = STRINGS[st.session_state.selected_lang]

        st.markdown("---")

        st.subheader(strings["model_label"])
        model_options = {"ollama": strings["ollama"], "gemini": strings["gemini"]}
        selected_model_display = st.selectbox(
            "",
            options=list(model_options.keys()),
            format_func=lambda x: model_options[x],
            index=0 if st.session_state.selected_model == "ollama" else 1,
            key="model_selector"
        )
        if selected_model_display != st.session_state.selected_model:
            st.session_state.selected_model = selected_model_display

        st.markdown("---")

        st.subheader(strings["add_docs_label"])
        uploaded_file = st.file_uploader("", type=["pdf"], accept_multiple_files=False, key="pdf_uploader")

        if uploaded_file is not None and st.session_state.uploaded_file_name != uploaded_file.name:
            st.session_state.uploaded_file_name = uploaded_file.name
            with st.spinner(strings["upload_and_process"]):
                files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
                try:
                    resp = requests.post(f"{BACKEND_URL}/api/rag/upload_pdf", files=files)
                    if resp.ok:
                        pages_processed = resp.json().get('pages', '?')
                        st.success(strings["upload_success"].format(pages=pages_processed))
                    else:
                        st.error(strings["upload_failed"])
                        st.session_state.uploaded_file_name = None
                except requests.exceptions.ConnectionError:
                    st.error("Could not connect to the backend. Please ensure the backend is running.")
                    st.session_state.uploaded_file_name = None
            st.rerun()

        if st.session_state.uploaded_file_name:
            st.markdown(f"**{st.session_state.uploaded_file_name}** (77 MB)")
            col_doc_btn1, col_doc_btn2 = st.columns(2)
            with col_doc_btn1:
                st.button(strings["upload_btn"], key="doc_upload_btn", disabled=True)
            with col_doc_btn2:
                if st.button(strings["reset_btn"], key="doc_reset_btn"):
                    st.session_state.uploaded_file_name = None
                    st.rerun()
        st.markdown("---")


    # --- Main Content Area ---
    st.markdown("<h2 style='text-align: center;'>Local RAG Chatbot</h2>", unsafe_allow_html=True)

    if page == "Chat":
        chat_container = st.container()
        with chat_container:
            st.subheader(strings["chat_header"])
            st.divider()

            display_chat_messages(strings)

        with st.form("chat_input_form", clear_on_submit=True):
            user_query = st.text_input("QA", placeholder=strings["chat_placeholder"], label_visibility="visible")
            submitted = st.form_submit_button("Send", help=strings["send_button"])

            if submitted and user_query:
                add_message("user", user_query)
                with st.chat_message("user"):
                    st.write(user_query)

                with st.chat_message("assistant"):
                    with st.spinner(strings["thinking"]):
                        data = {"query": user_query, "model": st.session_state.selected_model, "lang": st.session_state.selected_lang}
                        try:
                            resp = requests.post(f"{BACKEND_URL}/api/rag/chat", json=data)
                            if resp.ok:
                                answer = resp.json().get("answer", strings["no_answer"])
                            else:
                                answer = strings["error_backend"] + f" (Status: {resp.status_code})"
                        except requests.exceptions.ConnectionError:
                            answer = "Could not connect to the backend. Please ensure the backend is running."
                        except Exception as e:
                            answer = f"An unexpected error occurred: {e}"

                        add_message("assistant", answer)
                        st.write(answer)
                st.rerun()


        st.markdown("---")
        col_bottom1, col_bottom2, col_bottom3, col_bottom4 = st.columns(4)

        with col_bottom1:
            if st.button(strings["hide_setting_btn"], use_container_width=True):
                if st.session_state.settings_visible:
                    st.session_state.settings_visible = False
                    st.experimental_set_query_params(sidebar="collapsed")
                else:
                    st.session_state.settings_visible = True
                    st.experimental_set_query_params(sidebar="expanded")
                st.rerun()

        with col_bottom2:
            if st.button(strings["undo_btn"], use_container_width=True):
                if len(st.session_state.chat_history) >= 2:
                    st.session_state.chat_history.pop()
                    st.session_state.chat_history.pop()
                    st.rerun()
                elif len(st.session_state.chat_history) == 1:
                    st.session_state.chat_history.pop()
                    st.rerun()

        with col_bottom3:
            if st.button(strings["clear_btn"], use_container_width=True):
                clear_chat()
                st.rerun()

        with col_bottom4:
            if st.button(strings["reset_chat_btn"], use_container_width=True):
                clear_chat()
                st.session_state.uploaded_file_name = None
                st.rerun()

    elif page == "QA Section":
        st.title(strings["qa_section_title"])
        st.markdown(strings["qa_section_description"])
        


    st.markdown("<p style='text-align: center; color: gray;'>Built with Streamlit</p>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()