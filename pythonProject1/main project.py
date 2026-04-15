import tkinter as tk
from google import genai
from pygments.lexer import words
import threading
import data_helpers
import requests


#this will be how it gets stuff from a server, when this all happens, records.json in here will be deleted
#import requests

SERVER_URL = "https://recycling-server-ykk0.onrender.com"
def get_records():
    try:
        return requests.get(f"{SERVER_URL}/get").json()
    except:
        return []

#records = requests.get(url)
#data = records.json()
# ai stuff


DATA_FILE = "records.json"
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

# main part
records = get_records()

def button_pressed():
    try:
        item = entry1.get().lower().strip()

        # handle empty input
        if not item:
            label2.config(text="Please enter an item.")
            entry1.delete(0, tk.END)
            return

        # send request to Flask server
        response = requests.post(
            f"{SERVER_URL}/check",
            json={"item": item}
        )

        result = response.json()

        # handle server response
        if result["found"]:
            output = result["result"]
        else:
            output = "No result found."

    except Exception as e:
        output = f"Something went wrong: {e}"
        print(e)

        # update UI
    label2.config(text=output)
    entry1.delete(0, tk.END)
#tk stuff

def on_change(*args):
    current_text = entry_var.get().lower()

    best_score = -1
    second_best_score = -1
    third_best_score = -1

    best_word = ""
    second_best_word = ""
    third_best_word = ""

    suggested_words = []

    # clear UI
    for widget in suggestion_frame.winfo_children():
        widget.destroy()
    suggestion_frame.pack_forget()

    if not current_text.strip():
        return

    # GET DATA FROM SERVER


    for record in records:
        word = record["item"].lower()

        if not word.startswith(current_text):
            continue

        score = 0
        score += record.get("searched", 0)

        typed_letters = list(current_text)
        word_letters = list(word)

        length_to_check = min(len(word_letters), len(typed_letters))

        for i in range(length_to_check):
            if word_letters[i] == typed_letters[i]:
                score += 5

        if score >= best_score:
            third_best_score = second_best_score
            third_best_word = second_best_word

            second_best_score = best_score
            second_best_word = best_word

            best_score = score
            best_word = word

        elif score >= second_best_score:
            third_best_score = second_best_score
            third_best_word = second_best_word

            second_best_score = score
            second_best_word = word

        elif score >= third_best_score:
            third_best_score = score
            third_best_word = word

    if best_score != -1:
        suggested_words.append(best_word)
    if second_best_score != -1:
        suggested_words.append(second_best_word)
    if third_best_score != -1:
        suggested_words.append(third_best_word)

    if suggested_words:
        suggestion_frame.pack(pady=5)

    def set_selected(value):
        entry1.delete(0, tk.END)
        entry1.insert(0, value)

    for suggestion in suggested_words:
        btn = tk.Button(
            suggestion_frame,
            text=suggestion,
            width=30,
            command=lambda s=suggestion: set_selected(s)
        )
        btn.pack(pady=2)


root = tk.Tk()
root.title("Recycling Project Data Storing")
entry_var = tk.StringVar()
entry_var.trace_add("write", on_change)
frame1 = tk.Frame(root, bg="blue", bd=2, relief="solid")
frame1.pack(pady=5)
frame2 = tk.Frame(root, bg="blue", bd=2, relief="solid")
frame2.pack(pady=5)
label1 = tk.Label(frame1, text="Please input the item you want to dispose of")
label1.pack()
entry1 = tk.Entry(frame2, textvariable=entry_var)
entry1.pack()
tk.Button(frame2, text="Search", command=button_pressed).pack(padx=2, pady=2)
suggestion_frame = tk.Frame(root, bd=2, relief="solid")
suggestion_frame.pack(pady=5)

label2 = tk.Label(root, text="")
label2.pack()

root.mainloop()

#data= records.json
#requests.put(url, json=data)