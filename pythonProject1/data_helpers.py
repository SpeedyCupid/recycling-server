
from google import genai
import json
import os


DATA_FILE = "records.json"

# AI setup
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
def load_data():
    """
    Load all records from the JSON file.
    Returns an empty list if the file does not exist yet.
    """
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)
def save_data(records):
    with open(DATA_FILE, "w") as f:
        json.dump(records, f, indent=2)
def add_record(records, new_record):
    records.append(new_record)
    save_data(records)
    return records
def check_item(records, key, value, ai_prompt_setup=None, client=None):
    """
    Checks if a record matches the given key/value pair in the local records.
    Returns a friendly string describing recyclability.
    If not found, optionally calls AI and returns its response.
    """
    for record in records:
        record_value = record.get(key)
        recyclable_str = record.get("recyclable")  # assumes JSON stores "True"/"False" as strings

        if record_value == value:
            # increment the 'searched' field
            record["searched"] = record.get("searched", 0) + 1





            # save the updated records to your JSON file
            save_data(records)

            status = (
                "recyclable" if recyclable_str == "True"
                else "special disposal" if recyclable_str == "SD"
                else "not recyclable"
            )
            return f"{record_value} is {status}"

    # If not found, call AI if setup provided
    if ai_prompt_setup is not None and client is not None:
        total_prompt = ai_prompt_setup + value
        response = chatbot(total_prompt, client)
        if response == "Not Recyclable":
            truth = "False"
        elif response == "Special Disposal":
            truth = "SD"
        else:
            truth = "True"
        add_record(records, {"item": value, "recyclable": truth, "searched":1})
        return f"{value} is {response}"

    # Not found and no AI
    return None
def get_most_searched(records):
    """
    Returns a list of records sorted by 'searched' in descending order.
    Always reflects the latest counts.
    """
    return sorted(records, key=lambda r: r.get("searched", 0), reverse=True)
