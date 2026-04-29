import json
import os
import sqlite3
import difflib
import nltk

from flask import Flask, request, jsonify
from dotenv import load_dotenv
from nltk.corpus import words as nltk_words
from words import CUSTOM_WORDS   # 👈 your external word list

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

def correct_word(word):
    match = difflib.get_close_matches(word, WORD_POOL, n=1, cutoff=0.8)
    return match[0] if match else word


def correct_phrase(text):
    parts = text.lower().split()
    return " ".join(correct_word(p) for p in parts)

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
                "result": f"{value}{row[0]}"
            })

        # ===== 2. SPELLCHECK (NO AI) =====
        if not confirmed:
            corrected_phrase = correct_phrase(value)

            if corrected_phrase != value:
                return jsonify({
                    "needs_confirmation": True,
                    "original": value,
                    "suggestion": corrected_phrase
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
                "result": f"{final_name}{row[0]}"
            })

        # ===== 4. FALLBACK (NO AI RELIANCE REQUIRED) =====
        response = f"{final_name} should be brought to the Lincoln transfer station for proper disposal."

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