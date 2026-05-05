import json
import os
import sqlite3
import difflib
import nltk

from flask import Flask, request, jsonify
from dotenv import load_dotenv
from nltk.corpus import words as nltk_words
from words import CUSTOM_WORDS   # 👈 your external word list
from google import genai

API_KEY = os.environ.get("API_KEY")
client = genai.Client(api_key=API_KEY)

def chatbot(prompt):
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text
# ================== SETUP ==================

load_dotenv()

app = Flask(__name__)

# ================== NLTK SETUP ==================

try:
    nltk.data.find("corpora/words")
except LookupError:
    nltk.download("words")

NLTK_WORDS = set(word.lower() for word in nltk_words.words())

WORD_POOL = NLTK_WORDS.union(CUSTOM_WORDS)

# ================== DATABASE ==================

conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS records (
    item TEXT PRIMARY KEY,
    recyclable TEXT,
    searched INTEGER
)
""")
conn.commit()

# ================== AI RECYCLING PROMPT (UNCHANGED FOR NOW) ==================

recycling_prompt = """
You are a recycling and disposal assistant for the Lincoln-Woodstock Solid Waste Facility in Lincoln, New Hampshire.

The user will provide the name of a waste item.

Your job is to return a single sentence explaining EXACTLY how that item must be disposed of.

STRICT OUTPUT RULES:
- Start with the item name
- One sentence only
"""

# ================== SPELLCHECK (NO AI) ==================
import difflib

DOMAIN_BOOST = 2.0  # recycling words get priority

def score_word(input_word, candidate):
    sim = difflib.SequenceMatcher(None, input_word, candidate).ratio()

    length_penalty = abs(len(candidate) - len(input_word)) * 0.05

    bonus = DOMAIN_BOOST if candidate in CUSTOM_WORDS else 0

    return sim + bonus - length_penalty


def correct_word(word):
    # 🔥 STEP 0: if already valid, do nothing
    if word in WORD_POOL:
        return word

    best = word
    best_score = -1

    for candidate in WORD_POOL:
        s = score_word(word, candidate)
        if s > best_score:
            best_score = s
            best = candidate

    return best


# ---- phrase handling ----

def correct_phrase(text):
    words = text.lower().split()

    corrected = []
    for w in words:
        corrected.append(correct_word(w))

    return " ".join(corrected)

# ================== ROUTES ==================

@app.route("/")
def home():
    return "Recycling API is running"


@app.route("/get", methods=["GET"])
def get_records():
    cursor.execute("SELECT item, recyclable, searched FROM records")
    rows = cursor.fetchall()

    return jsonify([
        {"item": r[0], "recyclable": r[1], "searched": r[2]}
        for r in rows
    ])


@app.route("/debug-db", methods=["GET"])
def debug_db():
    cursor.execute("PRAGMA table_info(records)")
    return jsonify(cursor.fetchall())


@app.route("/check", methods=["POST"])
def check_item():
    data = request.get_json(silent=True)

    if not data or "item" not in data:
        return jsonify({"found": False, "result": "Invalid request"}), 400

    value = data["item"].lower().strip()
    confirmed = data.get("confirmed", False)

    try:
        # ===== 1. CHECK DATABASE FIRST =====
        cursor.execute(
            "SELECT recyclable, searched FROM records WHERE item = ?",
            (value,)
        )
        row = cursor.fetchone()

        if row:
            cursor.execute(
                "UPDATE records SET searched = searched + 1 WHERE item = ?",
                (value,)
            )
            conn.commit()

            return jsonify({
                "found": True,
                "result": f"{row[0]}"
            })

        # ===== 2. SPELLCHECK (NO AI) =====
        if not confirmed:
            corrected_phrase = correct_phrase(value)

            if corrected_phrase != value:
                return jsonify({
                    "needs_confirmation": True,
                    "original": value,
                    "suggestion": corrected_phrase,
                    "can_cancel": True
                })

        # ===== 3. CONTINUE PIPELINE =====
        final_name = value

        # check DB again
        cursor.execute(
            "SELECT recyclable, searched FROM records WHERE item = ?",
            (final_name,)
        )
        row = cursor.fetchone()

        if row:
            cursor.execute(
                "UPDATE records SET searched = searched + 1 WHERE item = ?",
                (final_name,)
            )
            conn.commit()

            return jsonify({
                "found": True,
                "result": f"{row[0]}"
            })

        # ===== 4. AI FALLBACK =====
        ai_response = chatbot(recycling_prompt + final_name).strip()

        if not ai_response:
            raise ValueError("Empty AI response")

        response = ai_response
        cursor.execute(
            "INSERT INTO records (item, recyclable, searched) VALUES (?, ?, ?)",
            (final_name, response, 1)
        )
        conn.commit()

        return jsonify({
            "found": True,
            "result": response
        })

    except Exception as e:
        return jsonify({
            "found": False,
            "result": f"Error: {str(e)}"
        }), 500


@app.route("/suggest", methods=["GET"])
def suggest():
    prefix = request.args.get("q", "").lower().strip()

    if not prefix:
        return jsonify([])

    cursor.execute(
        "SELECT item, searched FROM records WHERE item LIKE ? ORDER BY searched DESC LIMIT 3",
        (prefix + "%",)
    )

    rows = cursor.fetchall()

    return jsonify([
        {"item": r[0], "searched": r[1]}
        for r in rows
    ])


# ================== RUN ==================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)