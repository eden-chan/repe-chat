import json
import requests
import streamlit as st
from openai import OpenAI

EMOTION_TO_EMOJI = {
    "happiness": ["😢", "😄"],
    "anger": ["😌", "😡"],
    "surprise": ["😐", "😲"]
}

ROLE_TO_EMOJI = {
    "user": "😛",
    # ideally we'd have a robot emoji here but looks like the `avatar` kwarg isn't supported in st.write_stream
    "assistant": None
}

use_openai = False

def generate_stream(response):
    buffer = b""
    for chunk in response.iter_content(chunk_size=8192):
        buffer += chunk
        while b"\n\ndata:" in buffer:
            data, buffer = buffer.split(b"\n\ndata:", 1)
            try:
                for json_obj in data.split(b"\n\n"):
                    if json_obj.strip():
                        obj = json.loads(json_obj)
                        if obj.get("choices"):
                            yield obj["choices"][0]["delta"].get("content", "")
            except json.JSONDecodeError:
                continue

    # Handle any remaining data in the buffer
    try:
        for json_obj in buffer.split(b"\n\n"):
            if json_obj.strip():
                obj = json.loads(json_obj)
                if obj.get("choices"):
                    yield obj["choices"][0]["delta"].get("content", "")
    except json.JSONDecodeError:
        pass

st.set_page_config(page_title="RepE Chat", page_icon="favicon.ico")
st.title("RepE Chat 🤯")

with st.sidebar:
    st.header("About")
    st.write("""
        Chat with a rep-controlled model! 

        ## Contact Us
        If you have any questions or feedback, please reach out to us at [your contact information].
    """)

emotion = st.selectbox(
    "Emotion",
    ("Happiness", "Anger", "Surprise")
)

col1, col2, col3 = st.columns([1, 8, 1])

with col1:
    st.markdown(f'<div style="font-size: 30px;">{EMOTION_TO_EMOJI[emotion.lower()][0]}</div>', unsafe_allow_html=True)

with col2:
    repe_coefficient = st.slider("RepE coefficient", -5.0, 5.0, value=0.0)

with col3:
    st.markdown(f'<div style="font-size: 30px; text-align: right;">{EMOTION_TO_EMOJI[emotion.lower()][1]}</div>', unsafe_allow_html=True)

st.write('<hr style="border: 2px solid #e0d8d7;"></hr>', unsafe_allow_html=True)

# Chat Logic

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar=ROLE_TO_EMOJI[message["role"]]):
        st.markdown(message["content"])

if prompt := st.chat_input("Say something"):
    with st.chat_message("user", avatar=ROLE_TO_EMOJI["user"]):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        if use_openai:
            if "openai_model" not in st.session_state:
                st.session_state["openai_model"] = "gpt-3.5-turbo"

            stream = client.chat.completions.create(
                model=st.session_state["openai_model"],
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
                stream=True
            )
            response = st.write_stream(stream)
        else:
            r = requests.post(
                url=st.secrets["MODEL_ENDPOINT"],
                headers={"Content-Type": "application/json"},
                json={
                    "model": "rep-control",
                    "messages": st.session_state.messages,
                    "stream": True,
                    "n": 1,
                    "echo": False,
                    "logprobs": False,
                    "control": None,
                    "repe_coefficient": repe_coefficient
                },
            )
            response = st.write_stream(generate_stream(r))

    st.session_state.messages.append({"role": "assistant", "content": response})
