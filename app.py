import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from google import genai
from google.genai import types

import chatbot_config as config

load_dotenv()

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
MAX_MESSAGE_LENGTH = 2000
MAX_HISTORY_ITEMS = 20

app = Flask(__name__)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def text_content(role, text):
    return types.Content(role=role, parts=[types.Part.from_text(text=text)])


def build_contents(history, message):
    contents = []
    for item in history[-MAX_HISTORY_ITEMS:]:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        role = "model" if item.get("role") == "model" else "user"
        contents.append(text_content(role, text[:4000]))

    while contents and contents[0].role == "model":
        contents.pop(0)

    contents.append(text_content("user", message))
    return contents


@app.route("/")
def index():
    return render_template(
        "index.html",
        title=config.CHATBOT_TITLE,
        tagline=config.TAGLINE,
        icon=config.ICON,
        theme=config.THEME,
        suggestions=config.SUGGESTIONS,
    )


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()[:MAX_MESSAGE_LENGTH]
    history = data.get("history", [])

    if not message:
        return jsonify(error="Please type a question first."), 400
    if not isinstance(history, list):
        history = []

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=build_contents(history, message),
            config=types.GenerateContentConfig(
                system_instruction=config.SYSTEM_PROMPT,
                temperature=0.5,
                max_output_tokens=2048,
            ),
        )
        reply = (response.text or "").strip() or config.FALLBACK_REPLY
        return jsonify(reply=reply)
    except Exception:
        app.logger.exception("Gemini request failed")
        return (
            jsonify(error="The answer could not be generated right now. Please try again in a moment."),
            502,
        )


if __name__ == "__main__":
    app.run(debug=True)
