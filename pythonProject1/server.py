import json
import os
import difflib
import nltk

from flask import Flask, request, jsonify
from dotenv import load_dotenv
from nltk.corpus import words as nltk_words
from words import CUSTOM_WORDS
from google import genai
from supabase import create_client

# ================== SETUP ==================

load_dotenv()

app = Flask(__name__)

# ================== GEMINI ==================

API_KEY = os.environ.get("API_KEY")
client = genai.Client(api_key=API_KEY)

def chatbot(prompt):
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

# ================== SUPABASE ==================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ================== NLTK SETUP ==================

try:
    nltk.data.find("corpora/words")
except LookupError:
    nltk.download("words")

NLTK_WORDS = set(word.lower() for word in nltk_words.words())
WORD_POOL = NLTK_WORDS.union(CUSTOM_WORDS)

# ================== PROMPTS ==================

recycling_prompt = """
You are a recycling and disposal assistant for the Lincoln-Woodstock Solid Waste Facility in Lincoln, New Hampshire.

The user will provide the name of a waste item.

Your job is to return a single sentence explaining EXACTLY how that item must be disposed of.

STRICT OUTPUT RULES:
- Start with the item name
- One sentence only
"""

# ================== SPELLCHECK (UNCHANGED) ==================

DOMAIN_BOOST = 2.0

def score_word(input_word, candidate):
    sim = difflib.SequenceMatcher(None, input_word, candidate).ratio()
    length_penalty = abs(len(candidate) - len(input_word)) * 0.05
    bonus = DOMAIN_BOOST if candidate in CUSTOM_WORDS else 0
    return sim + bonus - length_penalty

def correct_word(word):
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

def correct_phrase(text):
    words = text.lower().replace("-", " ").split()
    return " ".join(correct_word(w) for w in words)

# ================== ROUTES ==================

@app.route("/")
def home():
    return "Recycling API is running"

# ------------------ GET ALL ------------------

@app.route("/get", methods=["GET"])
def get_records():
    res = supabase.table("records").select("*").execute()
    return jsonify(res.data)

# ------------------ DEBUG ------------------

@app.route("/debug-db", methods=["GET"])
def debug_db():
    return jsonify({"supabase": "active"})

# ------------------ CHECK ITEM ------------------

@app.route("/check", methods=["POST"])
def check_item():
    data = request.get_json(silent=True)

    if not data or "item" not in data:
        return jsonify({"found": False, "result": "Invalid request"}), 400

    value = data["item"].lower().strip()
    confirmed = data.get("confirmed", False)

    try:
        # ===== 1. CHECK DATABASE FIRST =====
        res = supabase.table("records").select("*").eq("item", value).execute()
        row = res.data[0] if res.data else None

        if row:
            supabase.table("records").update({
                "searched": row["searched"] + 1
            }).eq("item", value).execute()

            return jsonify({
                "found": True,
                "result": row["recyclable"]
            })

        # ===== 2. SPELLCHECK =====
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

        res = supabase.table("records").select("*").eq("item", final_name).execute()
        row = res.data[0] if res.data else None

        if row:
            supabase.table("records").update({
                "searched": row["searched"] + 1
            }).eq("item", final_name).execute()

            return jsonify({
                "found": True,
                "result": row["recyclable"]
            })

        # ===== 4. AI FALLBACK (UNCHANGED) =====
        ai_response = (chatbot(recycling_prompt + final_name) or "").strip()

        if not ai_response:
            raise ValueError("Empty AI response")

        response = ai_response

        supabase.table("records").insert({
            "item": final_name,
            "recyclable": response,
            "searched": 1
        }).execute()

        return jsonify({
            "found": True,
            "result": response
        })

    except Exception as e:
        return jsonify({
            "found": False,
            "result": f"Error: {str(e)}"
        }), 500

# ------------------ SUGGEST ------------------

@app.route("/suggest", methods=["GET"])
def suggest():
    prefix = request.args.get("q", "").lower().strip()

    if not prefix:
        return jsonify([])

    res = supabase.table("records").select("*").ilike("item", f"{prefix}%").execute()
    rows = sorted(res.data, key=lambda x: x.get("searched", 0), reverse=True)[:3]

    return jsonify([
        {"item": r["item"], "searched": r["searched"]}
        for r in rows
    ])

# ================== RUN ==================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)