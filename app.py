# app.py

from flask import Flask, request, jsonify
from flask_cors import CORS
import spacy
import json
import os

# Setup
app = Flask(__name__)
CORS(app)
nlp = spacy.load("en_core_web_sm")

# Templates for exact or similar match (can add more at later point)
TEMPLATES = {
    "make a pie": [
        "Gather pie ingredients (flour, butter, fruit, etc.).",
        "Prepare the crust by mixing flour and butter.",
        "Roll out the dough and place it in a pie dish.",
        "Prepare the filling (fruit, sugar, spices).",
        "Pour filling into the crust.",
        "Cover with top crust if needed and seal edges.",
        "Bake the pie until golden brown.",
        "Let the pie cool and serve."
    ],
    "study for an exam": [
        "Identify the exam topics.",
        "Gather study materials (notes, textbooks).",
        "Create a study schedule.",
        "Review notes and textbooks.",
        "Take practice tests.",
        "Focus on weak areas.",
        "Get enough rest before the exam."
    ]
}

# Generic flows for broad categories (set words that the code looks out for can add more)
GENERIC_FLOWS = {
    "cook": [
        "Gather all necessary ingredients and utensils.",
        "Prepare the ingredients by washing, chopping, and measuring.",
        "Follow the cooking steps according to your recipe.",
        "Check the food is cooked thoroughly.",
        "Serve the food and clean up the workspace."
    ],
    "clean": [
        "Gather cleaning supplies.",
        "Declutter the area you want to clean.",
        "Dust and wipe surfaces.",
        "Vacuum or sweep the floors.",
        "Dispose of waste and return items to their place."
    ],
    "study": [
        "Determine what subjects or topics you need to cover.",
        "Gather study materials and resources.",
        "Create a study timetable with breaks.",
        "Review material and take notes.",
        "Test yourself to reinforce your knowledge."
    ]
}

# Load learned tasks (user-trained)
if os.path.exists("learned_tasks.json"):
    with open("learned_tasks.json") as f:
        LEARNED_TASKS = json.load(f)
else:
    LEARNED_TASKS = {}

def save_learned_tasks():
    with open("learned_tasks.json", "w") as f:
        json.dump(LEARNED_TASKS, f, indent=2)

# Tone instructions
TONE_STYLES = {
    "pirate": lambda s: f"Arrr! {s} 🏴‍☠️",
    "girlypop": lambda s: f"Omg! {s} ✨💖",
    "academic": lambda s: f"Academic step: {s}",
    "calm": lambda s: f"Take a deep breath. {s}.",
    "hype": lambda s: f"Let's go! {s} 💪🔥",
    "slang": lambda s: f"Yo, just {s.lower()}, bruh."
}

# Fallback for totally unknown tasks
def fallback_steps(task):
    doc = nlp(task)
    verbs = [token for token in doc if token.pos_ == "VERB"]
    nouns = [token for token in doc if token.pos_ == "NOUN"]
    steps = []
    for verb in verbs:
        for noun in nouns:
            if noun.head == verb or noun in verb.children:
                steps.append(f"{verb.lemma_.capitalize()} the {noun.text}.")
    if not steps:
        steps = [f"Start by understanding how to '{task}'.",
                 "Break it into smaller actions.",
                 "Execute each action step-by-step.",
                 "Review and finish up."]
    return steps

# Generic matcher
def match_generic(task):
    doc = nlp(task)
    for keyword, flow in GENERIC_FLOWS.items():
        if any(keyword in t.lemma_ for t in doc):
            return flow
    return None

@app.route("/generate", methods=["POST"])
def generate_subtasks():
    data = request.get_json()
    task = data.get("task", "").lower()
    tone = data.get("tone", "academic").lower()

    steps = None

    # 1) Check learned tasks
    if task in LEARNED_TASKS:
        steps = LEARNED_TASKS[task]
    else:
        # 2) Check templates by similarity
        doc = nlp(task)
        best_match = None
        best_score = 0.0
        for k in TEMPLATES:
            sim = nlp(k).similarity(doc)
            if sim > best_score:
                best_match = k
                best_score = sim
        if best_score > 0.7:
            steps = TEMPLATES[best_match]

        # 3) Check generic flows
        if not steps:
            steps = match_generic(task)

        # 4) Fallback steps
        if not steps:
            steps = fallback_steps(task)

    # Apply tone
    tone_fn = TONE_STYLES.get(tone, lambda s: s)
    styled_steps = [tone_fn(step) for step in steps]

    return jsonify({"subtasks": styled_steps})

@app.route("/learn", methods=["POST"])
def learn_task():
    data = request.get_json()
    task = data["task"].lower()
    steps = data["steps"]
    LEARNED_TASKS[task] = steps
    save_learned_tasks()
    return jsonify({"status": "learned", "task": task, "steps": steps})

if __name__ == "__main__":
    app.run(debug=True)
