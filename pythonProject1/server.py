import json

from flask import Flask, request, jsonify

from data_helpers import save_data
from google import genai

app = Flask(__name__)

records = []

#AI setup
recycling_prompt = """
You are a recycling assistant.

The user will give you the name of an item. Your job is to determine whether the item is recyclable.

Rules:
- Respond with ONLY one of these three options:
  - "Recyclable"
  - "Not Recyclable"
  - "Special Disposal"
- if recyclability varies by location or material, use "Not Recyclable".
- Do not explain answers

Item:
"""
API_KEY = "AIzaSyDYCkZMTxGsfKJT5VYNBGmIOZbP3xoF6V0"
client = genai.Client(api_key=API_KEY)


def chatbot(prompt, client):
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text

@app.route("/get", methods=["GET"])
def get_records():
    return jsonify(records)

@app.route("/add", methods=["POST"])
def add_record():
    data = request.json
    records.append(data)
    return {"status": "ok"}
@app.route("/clear", methods=["POST"])
def clear_records():
    records.clear()
    return {"status": "cleared"}
@app.route("/check", methods=["POST"])
@app.route("/check", methods=["POST"])
def check_item():
    data = request.get_json(silent=True)

    if not data or "item" not in data:
        return jsonify({
            "found": False,
            "result": "Invalid request"
        }), 400

    value = data["item"]

    # 1. search existing records
    for record in records:
        if record.get("item") == value:
            record["searched"] = record.get("searched", 0) + 1
            save_data(records)

            status = (
                "recyclable" if record["recyclable"] == "True"
                else "special disposal" if record["recyclable"] == "SD"
                else "not recyclable"
            )

            return jsonify({
                "found": True,
                "result": f"{value} is {status}"
            })

    # 2. NOT FOUND → AI
    try:
        total_prompt = recycling_prompt + value
        response = chatbot(total_prompt, client)

        if not response:
            raise ValueError("Empty AI response")

        if response == "Not Recyclable":
            truth = "False"
        elif response == "Special Disposal":
            truth = "SD"
        else:
            truth = "True"

        new_record = {
            "item": value,
            "recyclable": truth,
            "searched": 1
        }

        records.append(new_record)
        save_data(records)

        return jsonify({
            "found": True,
            "result": f"{value} is {response}"
        })

    except Exception as e:
        return jsonify({
            "found": False,
            "result": f"AI error: {str(e)}"
        }), 500
@app.route("/suggest", methods=["GET"])
def suggest():
    prefix = request.args.get("q", "").lower().strip()

    if not prefix:
        return jsonify([])

    matches = []

    for record in records:
        word = record.get("item", "").lower()

        if word.startswith(prefix):
            matches.append({
                "item": record["item"],
                "searched": record.get("searched", 0)
            })

    # sort by most searched (important)
    matches = sorted(matches, key=lambda x: x["searched"], reverse=True)

    # return top 3
    return jsonify(matches[:3])

import os
@app.route("/")
def home():
    return "Recycling API is running"
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)