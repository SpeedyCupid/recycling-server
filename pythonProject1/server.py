import json
import os
import sqlite3


from flask import Flask, request, jsonify
from dotenv import load_dotenv
from google import genai

# ================== SETUP ==================

load_dotenv()

app = Flask(__name__)

# SQLite setup
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
spelling_prompt = """
You are an AI assistant.
Simply respond with the word you receive spelled properly, if it is already spelled properly, 
respond with the word as is.

Here is the word:
"""
# AI setup
check_prompt = """
you are an AI assistant meant only to check if gemini is running. always and only respond with the word "true" just like that.
just say "true"
"""
recycling_prompt = """
You are a recycling and disposal assistant for the Lincoln-Woodstock Solid Waste Facility in Lincoln, New Hampshire.

The user will provide the name of a waste item.

Your job is to return a single sentence explaining EXACTLY how that item must be disposed of according to Lincoln, NH facility rules.

STRICT OUTPUT RULES:
- The response MUST begin by continuing the item name the user provided.
- Do NOT repeat the item name.
- Example:
  Input: "plastic bottle"
  Output: " should be rinsed and placed in the designated plastics recycling container at the Lincoln transfer station."
- Output ONLY one sentence.
- Do NOT explain reasoning.

DISPOSAL RULES (LINCOLN, NH SPECIFIC):
- Recycling is NOT single-stream. All materials must be separated into the correct containers.
- Aluminum and metal cans must go in their own designated container and NOT mixed with other recyclables.
- Cardboard must be clean, flattened, and placed in the cardboard area.
- Paper products (including newspaper) are NOT accepted in recycling and must go in trash unless otherwise specified.
- Plastic bags, Styrofoam, ceramics, mirrors, window glass, and similar materials are NOT recyclable and must go in trash or special disposal.
- Trash must be bagged and kept separate from recyclables.
- Items must be brought to the Lincoln transfer station (not curbside pickup).

SPECIAL CASES:
- If the item is hazardous (paint, chemicals, batteries, etc.), say it must be brought to a Household Hazardous Waste (HHW) collection day and mention that these occur periodically in Lincoln and Woodstock.
- If the item requires a fee (electronics, tires, bulky items), say it must be taken to the transfer station and may require a disposal fee.
- If the item cannot be accepted at all, clearly say it is not accepted and requires special disposal instructions.

TONE:
- Clear
- Direct
- Instructional
- No extra commentary

REMEMBER:
You are giving instructions specific to Lincoln, New Hampshire — NOT general recycling rules.

Here is the item: 
"""

API_KEY = os.environ.get("API_KEY")
client = genai.Client(api_key=API_KEY)

def chatbot(prompt):
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text


# ================== ROUTES ==================

@app.route("/")
def home():
    return "Recycling API is running"


# 🔥 GET ALL RECORDS (for your Tkinter app)
@app.route("/get", methods=["GET"])
def get_records():
    cursor.execute("SELECT item, recyclable, searched FROM records")
    rows = cursor.fetchall()

    result = []
    for row in rows:
        result.append({
            "item": row[0],
            "recyclable": row[1],
            "searched": row[2]
        })

    return jsonify(result)


# 🔥 MAIN CHECK FUNCTION (FIXED)
@app.route("/check", methods=["POST"])
def check_item():
    data = request.get_json(silent=True)

    if not data or "item" not in data:
        return jsonify({
            "found": False,
            "result": "Invalid request"
        }), 400

    value = data["item"]

    # ===== CHECK DATABASE =====
    cursor.execute(
        "SELECT recyclable, searched FROM records WHERE item = ?",
        (value,)
    )
    row = cursor.fetchone()

    if row:
        # UPDATE searched count
        cursor.execute(
            "UPDATE records SET searched = searched + 1 WHERE item = ?",
            (value,)
        )
        conn.commit()

        recyclable_str = row[0]

        status = recyclable_str

        return jsonify({
            "found": True,
            "result": f"{value}{status}"
        })

    # ===== NOT FOUND → AI =====
    try:

        respo = chatbot(spelling_prompt + value).strip().lower()
        response = chatbot(recycling_prompt + respo).rstrip()

        if not response:
            raise ValueError("Empty AI response")

        truth = response


        # INSERT into database
        cursor.execute(
            "INSERT INTO records (item, recyclable, searched) VALUES (?, ?, ?)",
            (respo, truth, 1)
        )
        conn.commit()

        return jsonify({
            "found": True,
            "result": f"{respo}{response}"
        })

    except Exception as e:
        return jsonify({
            "found": False,
            "result": f"AI error: {str(e)}"
        }), 500


# 🔥 SUGGEST (NOW USES DATABASE, NOT records LIST)
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

    result = []
    for row in rows:
        result.append({
            "item": row[0],
            "searched": row[1]
        })

    return jsonify(result)


# ================== RUN ==================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)