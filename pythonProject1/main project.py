import os
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
records = get_records()

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
API_KEY = os.environ.get("API_KEY")
client = genai.Client(api_key=API_KEY)

# main part


def button_pressed():
    global records

    try:
        item = entry1.get().lower().strip()

        if not item:
            label2.config(text="Please enter an item.")
            entry1.delete(0, tk.END)
            return

        response = requests.post(
            f"{SERVER_URL}/check",
            json={"item": item}
        )

        if response.status_code != 200:
            label2.config(text="Server error")
            print(response.text)
            return

        result = response.json()

        if result.get("found"):
            output = result.get("result")
        else:
            output = "No result found."

        # 🔥 IMPORTANT: refresh local data AFTER search
        try:
            records = get_records()
        except:
            pass

    except Exception as e:
        output = f"Something went wrong: {e}"
        print(e)

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

    # USE LOCAL records ONLY (NO SERVER CALL HERE)

    for record in records:
        word = record["item"].lower()

        if not word.startswith(current_text):
            continue

        score = record.get("searched", 0)

        typed_letters = list(current_text)
        word_letters = list(word)

        for i in range(min(len(word_letters), len(typed_letters))):
            if word_letters[i] == typed_letters[i]:
                score += 5

        if score >= best_score:
            third_best_score, third_best_word = second_best_score, second_best_word
            second_best_score, second_best_word = best_score, best_word
            best_score, best_word = score, word

        elif score >= second_best_score:
            third_best_score, third_best_word = second_best_score, second_best_word
            second_best_score, second_best_word = score, word

        elif score >= third_best_score:
            third_best_score, third_best_word = score, word

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
        tk.Button(
            suggestion_frame,
            text=suggestion,
            width=30,
            command=lambda s=suggestion: set_selected(s)
        ).pack(pady=2)

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
#
# #data= records.json
# #requests.put(url, json=data)
#
# from google import genai
# import tkinter as tk
# import json
# import os
# import data_helpers
#
# DATA_FILE = "records.json"
#
#
# records = data_helpers.load_data()
#
# # ---------------- BUTTON PRESS ----------------
# def button_pressed():
#     try:
#         item = entry1.get()
#
#         if not item or not item.strip():
#             label2.config(text="Please enter an item.")
#             entry1.delete(0, tk.END)
#             return
#
#         item = item.lower().strip()
#
#         results = data_helpers.check_item(
#             records,
#             "item",
#             item,
#             data_helpers.recycling_prompt,
#             data_helpers.client
#         )
#
#         if results is None:
#             output = "No result found."
#         else:
#             output = results
#
#     except Exception as e:
#         output = f"Something went wrong: {e}"
#
#     label2.config(text=output)
#     entry1.delete(0, tk.END)
#
#
# # ---------------- SUGGESTIONS ----------------
# def on_change(*args):
#     current_text = entry_var.get().lower()
#
#     best_score = -1
#     second_best_score = -1
#     third_best_score = -1
#
#     best_word = ""
#     second_best_word = ""
#     third_best_word = ""
#
#     suggested_words = []
#
#     for widget in suggestion_frame.winfo_children():
#         widget.destroy()
#     suggestion_frame.pack_forget()
#
#     if not current_text.strip():
#         return
#
#     for record in records:
#         word = record["item"].lower()
#
#         if not word.startswith(current_text):
#             continue
#
#         score = record.get("searched", 0)
#
#         typed_letters = list(current_text)
#         word_letters = list(word)
#
#         length_to_check = min(len(word_letters), len(typed_letters))
#
#         for i in range(length_to_check):
#             if word_letters[i] == typed_letters[i]:
#                 score += 5
#
#         if score >= best_score:
#             third_best_score = second_best_score
#             third_best_word = second_best_word
#
#             second_best_score = best_score
#             second_best_word = best_word
#
#             best_score = score
#             best_word = word
#
#         elif score >= second_best_score:
#             third_best_score = second_best_score
#             third_best_word = second_best_word
#
#             second_best_score = score
#             second_best_word = word
#
#         elif score >= third_best_score:
#             third_best_score = score
#             third_best_word = word
#
#     if best_score != -1:
#         suggested_words.append(best_word)
#     if second_best_score != -1:
#         suggested_words.append(second_best_word)
#     if third_best_score != -1:
#         suggested_words.append(third_best_word)
#
#     if suggested_words:
#         suggestion_frame.pack(pady=5)
#
#     def set_selected(value):
#         entry1.delete(0, tk.END)
#         entry1.insert(0, value)
#
#     for suggestion in suggested_words:
#         btn = tk.Button(
#             suggestion_frame,
#             text=suggestion,
#             width=30,
#             command=lambda s=suggestion: set_selected(s)
#         )
#         btn.pack(pady=2)
#
#
# # ---------------- UI ----------------
# root = tk.Tk()
# root.title("Recycling Project Data Storing")
#
# entry_var = tk.StringVar()
# entry_var.trace_add("write", on_change)
#
# frame1 = tk.Frame(root, bg="blue", bd=2, relief="solid")
# frame1.pack(pady=5)
#
# frame2 = tk.Frame(root, bg="blue", bd=2, relief="solid")
# frame2.pack(pady=5)
#
# label1 = tk.Label(frame1, text="Please input the item you want to dispose of")
# label1.pack()
#
# entry1 = tk.Entry(frame2, textvariable=entry_var)
# entry1.pack()
#
# tk.Button(frame2, text="Search", command=button_pressed).pack(padx=2, pady=2)
#
# suggestion_frame = tk.Frame(root, bd=2, relief="solid")
# suggestion_frame.pack(pady=5)
#
# label2 = tk.Label(root, text="")
# label2.pack()
#
# root.mainloop()