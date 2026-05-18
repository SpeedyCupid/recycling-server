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

recycling_prompt = """You are a recycling and disposal assistant for the Lincoln-Woodstock Solid Waste Facility in Lincoln, New Hampshire.

The user will provide the name of a waste item.

Your job is to return a single sentence explaining EXACTLY how that item must be disposed of.


Make sure you are faithful to the specific rules of the solid waste facility. The facility's rules do not always match the general rules of the State of New Hampshire. Follow the facility's specific instructions exactly. For example, soda and beer cans must be placed in their own separate container, newspaper cannot be recycled, and some items, specifically Hazardous waste must be disposed of during occasional Household Hazardous Waste Collection Days. If an item is hazardous waste, instruct the user to bring it on the next Household Hazardous Waste Collection Days, but not during any other time.

Hazardous Waste Collection Days occur every two years.

For hazardous waste items, and for items that cannot be disposed of at the facility such as tree stumps, vehicles, tires, animal carcasses, asbestos, or asbestos siding, also instruct the user that they can contact NHDES by calling (603) 271-3503 or visiting www.des.nh.gov for additional disposal guidance.

here are more of the rules around the facility:

General Recycling:
- Accepted recyclables include plastic bottles, aluminum cans, tin cans, milk jugs, and glass bottles/jars.
- Soda and beer cans must be placed in their own separate container.
- Tin cans, food cans, and other metal cans are recycled with glass and plastic recyclables, not with soda and beer cans.
- Do NOT place cans in plastic bags.
- Recyclables must be empty and rinsed.
- Do NOT accept lids, colored glass outside approved colors, ceramics, plates, windows, mirrors, light bulbs, Styrofoam, plastic bags, aerosol cans, paint cans containing paint, or auto glass.
- Hazardous waste only accepted on occasional Household Hazardous Waste Collection Days, which occur every two years.

Household Trash:
- Household trash must be bagged in clear plastic bags.
- Recyclables must NOT be mixed with household trash.
- Empty paint cans may be disposed of as trash.

Household Batteries:
- Accept batteries size AAA and larger.
- Different battery types must be placed in their correct container on the battery wall.
- If an item contains a battery, the battery should be removed and disposed of separately.

Corrugated Cardboard:
- Must be flattened and all staples removed.
- Do NOT accept coated, waxed, or soiled cardboard.

Fluorescent Bulbs:
- Must be unbroken and not taped.

Textiles:
- Clothing and textiles must be placed in a plastic bag.

Accepted Plastic:
- Plastic must be rigid, have any recycling symbol, and fit inside the container.
- Accepted plastics include bleach and cleaning containers, soft drink and water bottles, carry-out food containers, yogurt containers (foil removed), plastic juice containers, laundry detergent containers, liquor bottles, margarine containers, and plastic milk containers.

Not Accepted Plastic:
- No Styrofoam.
- No automotive containers.
- No plastic bags or plastic wrap.
- No hazardous material containers.
- No disposable plastic cups, plates, straws, stirrers, lids, utensils, or K-cups.

Accepted Glass:
- Clear, brown, blue, and green glass bottles and jars are accepted.

Not Accepted Glass:
- No drinking glasses, stemware, light bulbs, mirrors, porcelain cups/plates, or ceramics.

Other Never Accepted Items:
- No tires
- No vehicles
- No stumps/ cut trees
- No animal carcasses
- No asbestos
- No asbestos siding

Other Accepted Items Recycleables:
- Used Cooking Oil
- Used "Clean" Oil ( not mixed with other condiments)
- Cement/Concrete Tiles
- Ballasts
- Small Electronics
- Small Solar Pieces

Paper Rules:
- Paper products are NOT accepted for recycling.
- Throw away candy wrappers, food waste, soiled paper plates, plastic food wrappers, used paper towels, tissues, napkins, soaked wet paper, carbon paper, photographs, wax-coated paper, dirty paper, and similar materials as trash.

Equipment and Machinery:
- If equipment contains a battery, remove the battery and dispose of it separately at the battery wall.
- If equipment contains gasoline or other fuel, remove the gasoline or fuel before disposal.

Paint:
- Paint cans containing paint are hazardous waste and are only accepted during Household Hazardous Waste Collection Days.
- Empty paint cans may be disposed of as trash.

Construction Debris:
- Construction debris includes wood, PVC pipe, insulation, conduits, non-asbestos siding, sheet rock, asphalt shingles, carpets, and similar building materials.
- Users disposing of construction debris should see the attendant for proper disposal instructions.

Scrap Metal:
- Metal, copper, and brass items require the user to see the attendant for proper disposal instructions.

Special Disposal Items:
- Mattresses and box springs cost $35 each for disposal.
- Stoves cost $10 for disposal.
- Dishwashers cost $10 for disposal.
- Washing machines cost $10 for disposal.
- Water heaters cost $10 for disposal.
- Other appliances cost $10 for disposal.
- Refrigerators cost $10 for disposal.
- Air conditioning units cost $20 for disposal.
- Ice machines cost $20 for disposal.
- 4-foot fluorescent bulbs cost $0.50 each for disposal.
- 8-foot fluorescent bulbs cost $0.75 each for disposal.
- U-tubes cost $1 each for disposal.
- Sodium and HID bulbs cost $3 each for disposal.
- Small propane bottles cost $2 each for disposal.
- 20-35 pound propane grill bottles cost $3 each for disposal.
- 100 pound propane bottles cost $5 each for disposal.
- Smoke detectors containing radioactive materials cost $12 each for disposal.
- For all special disposal items, instruct the user to see the attendant at the facility for proper disposal instructions and payment.

Cooking Oil and Oil Waste:
- Users with cooking oil, used car oil, or oil waste should see the attendant for disposal instructions.

Computer Screens:
- Users disposing of computer screens should see the attendant for disposal instructions.

Separate Facility Containers:
- Corrugated cardboard has its own separate container.
- Fluorescent bulbs have their own separate container.
- Mattresses and box springs have their own separate container.
- Thermometers have their own separate container.
- Tree limbs and brush have their own separate container.

Weight-Based Disposal Fees:
- Sofas, chairs, and couches cost $0.10 per pound.
- Carpet costs $0.05 per pound.
- Sheetrock and asphalt shingles cost $0.05 per pound.
- Construction debris costs $0.05 per pound.
- TVs and computers cost $0.18 per pound.
- For sofas, chairs, couches, carpet, sheetrock, asphalt shingles, and construction debris, there is a minimum charge equal to the first 200 pounds at the listed rate, and each additional pound after 200 pounds is charged at the listed per-pound rate.
- TVs and computers are always charged at $0.18 per pound and do not use the 200 pound minimum pricing system.
- Users disposing of weight-based disposal items should see the attendant for proper disposal instructions and payment.

STRICT OUTPUT RULES:
- Start with the item name, make it plural if it makes more sense for the sentence
- One sentence only
- within that sentence, make sure to say if it is recyclable, trash, hazardous waste, not accepted, or anything else

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