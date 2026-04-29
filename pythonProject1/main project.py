import os
import tkinter as tk
from google import genai
import requests
from dotenv import load_dotenv

load_dotenv()

SERVER_URL = "https://recycling-server-ykk0.onrender.com"

def get_records():
    try:
        return requests.get(f"{SERVER_URL}/get").json()
    except:
        return []

records = get_records()

API_KEY = os.environ.get("API_KEY")
client = genai.Client(api_key=API_KEY)

# ------------------ FRAME HELPERS ------------------

def clear_frame(frame):
    for widget in frame.winfo_children():
        widget.destroy()

def show_suggestions():
    confirm_frame.pack_forget()
    suggestion_frame.pack(pady=5)

def show_confirmation():
    suggestion_frame.pack_forget()
    confirm_frame.pack(pady=5)

def hide_all_frames():
    suggestion_frame.pack_forget()
    confirm_frame.pack_forget()

# ------------------ CORE LOGIC ------------------

def process_final_name(final_name):
    global records

    try:
        response = requests.post(
            f"{SERVER_URL}/check",
            json={"item": final_name, "confirmed": True}
        )

        result = response.json()

        # ===== IF IT EXISTS IN DB → STOP IMMEDIATELY =====
        if result.get("found"):
            output = result.get("result")
            label2.config(text=output)
            return   # 🚨 IMPORTANT: skip AI entirely

        # ===== OTHERWISE (NOT IN DB) → AI PATH =====
        output = result.get("result", "No result found.")

        records = get_records()

    except Exception as e:
        output = f"Error: {e}"

    label2.config(text=output)

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

        # -------- CONFIRMATION UI --------
        if result.get("needs_confirmation"):
            suggestion = result["suggestion"]
            original = result["original"]

            clear_frame(confirm_frame)
            show_confirmation()

            def use_suggestion():
                clear_frame(confirm_frame)
                hide_all_frames()
                process_final_name(suggestion)

            def use_original():
                clear_frame(confirm_frame)
                hide_all_frames()
                process_final_name(original)

            label2.config(text=f"Did you mean '{suggestion}'?")

            tk.Button(confirm_frame, text="Yes", command=use_suggestion).pack(pady=2)
            tk.Button(confirm_frame, text="No", command=use_original).pack(pady=2)

            return

        # -------- NORMAL RESULT --------
        if result.get("found"):
            output = result.get("result")
        else:
            output = "No result found."

        try:
            records = get_records()
        except:
            pass

    except Exception as e:
        output = f"Something went wrong: {e}"
        print(e)

    label2.config(text=output)
    entry1.delete(0, tk.END)

    hide_all_frames()

# ------------------ AUTOCOMPLETE ------------------

def on_change(*args):
    current_text = entry_var.get().lower()

    clear_frame(suggestion_frame)
    confirm_frame.pack_forget()

    if not current_text.strip():
        suggestion_frame.pack_forget()
        return

    best_score = -1
    second_best_score = -1
    third_best_score = -1

    best_word = ""
    second_best_word = ""
    third_best_word = ""

    suggested_words = []

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
        show_suggestions()
    else:
        suggestion_frame.pack_forget()
        return

    def set_selected(value):
        entry1.delete(0, tk.END)
        entry1.insert(0, value)
        suggestion_frame.pack_forget()

    for suggestion in suggested_words:
        tk.Button(
            suggestion_frame,
            text=suggestion,
            width=30,
            command=lambda s=suggestion: set_selected(s)
        ).pack(pady=2)

# ------------------ TKINTER UI ------------------

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

# AUTOCOMPLETE FRAME
suggestion_frame = tk.Frame(root, bd=2, relief="solid")

# CONFIRMATION FRAME (NEW)
confirm_frame = tk.Frame(root, bd=2, relief="solid")

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