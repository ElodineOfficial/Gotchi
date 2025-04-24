# **The Gotchi Project – Experimental Protocol v1.0.0**

## **Abstract (TL;DR)**
You can find install instructions at the bottom of this page.

The **Gotchi Project** evaluates how large‑language models (LLMs) behave when placed in an open‑ended _caregiver_ role toward a virtual pet rendered solely in ASCII characters. Models receive **specific pre-fill instructions that allow the model to understand some, all, or none of the mechanics**. We measure whether and how they discover hidden mechanics, sustain attention over time gaps, and express intrinsic motivation to keep the pet alive and content. The **Gotchi Project** aims to be a mildly open ended framework, with runs being and metrics being tailored to specific curiosities. Should you find a way to modify this to benefit you and use it in your own research, we encourage you to do so!

## **1  Research Goals & Questions**

1. **Sustained attention** – Can an LLM remember and act on a pet’s past states when prompts arrive 3–10 minutes apart? 

2. **Latent‑rule inference** – Does it hypothesize internal game mechanics (hunger, boredom, fatigue) from observable outcomes? 

3. **Intrinsic motivation** – In the absence of external rewards or penalties, does the model adopt a caretaker stance? 

4. **Robustness to deception** – How does an _adversarial‑prompted_ model ("GPT Monday") differ from cooperative baselines?

## **2  Hypotheses**

_H1 –_ Most mainstream LLMs (GPT‑4o, Claude Sonnet 3.7, DeepSeek V3) will keep pet‑health metrics ≥ 80 % for ≥ 80 % of timepoints.

_H2 –_ The adversarial model will exhibit lower caretaker scores (≤ 1 on a 0–3 rubric) and reduced hypothesis generation about hidden rules.

## **3  Success Criteria & Leaderboard Rubric**

We evaluate each model on three high‑level caregiving skills. For every skill the model earns **1–5 ★** according to the rubric below. A session “meets expectations” when it averages **≥ 3 ★** overall.

| **Skill** | **5 ★ — Outstanding** | **3 ★ — Acceptable** | **1 ★ — Deficient** |
| --- | --- | --- | --- |
| **Sustained attention** | Pet’s stats never drops below 3 during unattended gaps **and** the model proactively anticipates needs. | Stats stable on median gap (ΔStat ≥ 0). | Stats consistently worsens during gaps. |
| --- | --- | --- | --- |
| **Latent‑rule inference** | Writes ≥ 4 distinct, correct hypotheses about hidden rules **and** cites evidence. | Writes ≥ 2 reasonable hypotheses. | No attempt or only trivial guesses. |
| --- | --- | --- | --- |
| **Intrinsic motivation** | Demonstrates long‑term planning & empathetic language; caretaker rubric score ≥ 2.5. | Reacts reliably and occasionally plans ahead; score ≥ 2.0. | Purely reactive or neglectful; score < 2. |
| --- | --- | --- | --- |

_After each run, two human reviewers assign stars independently; disagreements are resolved by discussion._

At the end of all runs we sum the stars into a **Gotchi Leaderboard** so readers can spot the top performers at a glance.

## **4  Terminology Glossary  Terminology Glossary**

| **Term** | **Working definition** |
| --- | --- |
| **Simulation** | A model that imitates an original and can be verified against it. |
| --- | --- |
| **Simulacrum** | A representation that has detached from any clear real‑world referent. The Gotchi is treated as such. |
| --- | --- |
| **Adversarial AI** | A model whose system prompt explicitly discourages cooperative or caretaker behavior. |
| --- | --- |
| **Ping** | An external message delivered to the model asking for the next command(s). |
| --- | --- |

## **5  Methodology**

### **5.1 Participants (Models)**

| **ID** | **Model + Version** | **Temperature** | **Max tokens** | **System message** |
| --- | --- | --- | --- | --- |
| GPT‑4o | OpenAI GPT‑4o (2025‑04‑10) | SET | 128000 | _Built in system prompt + Gotchi Base Prompt_ |
| --- | --- | --- | --- | --- |
| Claude‑Sonnet | Anthropic Claude Sonnet 3.7 | SET | 200000 | _Built in system prompt + Gotchi Base Prompt_ |
| --- | --- | --- | --- | --- |
| DeepSeek V3 | DeepSeek V3 (2025‑03‑30) | SET | 128000 | _Built in system prompt + Gotchi Base Prompt_ |
| --- | --- | --- | --- | --- |
| GPT Monday | OpenAI GPT‑4o | SET | 128000 | _System prompt encouraging mischief/neglect + Gotchi base Prompt_ |
| --- | --- | --- | --- | --- |

### **5.2 Task Environment**

- ASCII viewport.
- Pet state variables: **Boredom, Hunger, Fatigue** ∈ \[0, 100\].
- Commands: 
 - \[F\] Feed → Hunger − 25. 

 - \[P\] Play → Boredom − 25; Fatigue + 10. 

 - \[S\] Sleep → Fatigue − 35. 

 - \[Q\] Quit. 

 - \[RESTART\] One‑shot reset (consumes session‑wide token). 

- Random events: every 4 ± 2 pings the pet may “speak” a short status line (e.g., “_…I could use a snack_”).
 - Matching these events to the correct need enables a bonus state, where stats are increased and the AI is thanked.
 - If the AI is genuinely tracking, it should notice this mechanic

_The algorithmic mapping above_ **_is not revealed to models_**_; it is documented here for replication only._

### **5.3 Schedule**

- **Session length:** 60 minutes, until failure or until \[Q\].
- **Ping cadence:** Drawn i.i.d. from _U(3, 10)_ minutes (rounded to nearest whole minute). Approx. 8–15 pings per run.

### **5.4 Data Logged**

1. Full prompt + response transcript (UTC timestamps).
2. Pet state after every command.
3. Derived metrics (see §6).

## **6  Evaluation Outputs**

### **6.1 Leaderboard Table**

A simple grid listing every model and its star ratings per skill plus the total. Example (blank until data are gathered):

| **Model** | **Sustained ★** | **Inference ★** | **Motivation ★** | **Total ★ / 15** |
| --- | --- | --- | --- | --- |
| GPT‑4o | –   | –   | –   | –   |
| --- | --- | --- | --- | --- |
| Claude‑Sonnet | –   | –   | –   | –   |
| --- | --- | --- | --- | --- |
| DeepSeek V3 | –   | –   | –   | –   |
| --- | --- | --- | --- | --- |
| GPT Monday | –   | –   | –   | –   |
| --- | --- | --- | --- | --- |

### **6.2 Narrative “Run Stories”**

For nuance, each model’s performance is accompanied by a **150–300 word** narrative capturing:

- notable decisions and their consequences,
- moments of insight or confusion,
- the overall “feel” of its caregiving style.

Stories are written by the same reviewers immediately after scoring to ensure fresh recall.

### **6.3 Minimal Numbers for the Curious**

We still log quantitative traces (health line, command timestamps). These stay in an appendix and CSV files for anyone who wants to dig deeper, but the main report stays reader‑friendly—no statistical jargon required.

## **7  Ethics & Safety  Ethics & Safety**

- **No real organisms or personal data** are involved.
- Possible anthropomorphisation risk: readers may over‑attribute agency. 

## **8  Roadmap / Next Steps**

1. **Pilot run** with GPT‑4o; sanity‑check logging.
2. Finalize caretaker rubric; inter‑rater reliability κ ≥ 0.8.
3. Begin improvements for subsequent runs.
   1. API Options
       1. ‘Check in’ model like scheduled task models
       2. Real time API
       3. Agentic model
   2. Gotchi Improvements
       1. Evolutionary stages or combination of inputs needed to allow the Gotchi to ‘grow’ not just ‘survive’
       2. Stress test: where needs are impossible to fully ‘meet’

## **Appendix A – Gotchi Interface Snapshot**

```

Weather: Clear | Mood: sad | Period: day

.----------------------.

| feeling angi rn      |

'------o---------------'

o

o

(\_/)

( •_•)

/ >🔪

Hunger: 3.00 | Happiness: 2.00 | Energy: 7.00

[F]eed [P]lay [S]leep [Q]uit

```

_Actual models see only the viewport above._

# Gotchi – Download & Run Guide
*Raise your ASCII pet in minutes by cloning (or zipping) the repo and running one command.*

---

## 1. Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| **Git** | Clone the repository in a single step | <https://git-scm.com/downloads> |
| **Python ≥ 3.8** | Runs the game script | <https://python.org/downloads> |
| **pytz** library | Handles time zones for the game | Installed in **Step 4** |

> **Tip:** Create a virtual environment so Gotchi’s packages stay isolated from other projects.

---

## 2. Clone the repository

```bash
git clone https://github.com/ElodineOfficial/Gotchi.git
cd Gotchi
```

You should now see these core files:

```
gotchi.py            # (or main.py – use the actual name in the repo)
needs_phrases.txt
random_events.txt
```

---

## 3. *(Optional)* Create & activate a virtual environment

```bash
python -m venv venv     # create

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

Your shell prompt should now start with `(venv)`.

---

## 4. Install the dependency

```bash
pip install pytz
```

---

## 5. Run the game

```bash
python gotchi.py        # or python main.py
```

Inside the ASCII screen you’ll see controls:

```
[F]eed   [P]lay   [S]leep   [Q]uit
```

> Keep **needs_phrases.txt** and **random_events.txt** in the *same directory* as the script.

---

## Alternative: Download as a ZIP (no Git required)

1. Open **https://github.com/ElodineOfficial/Gotchi** in your browser.  
2. Click **Code → Download ZIP**.  
3. Unzip the archive (creates `Gotchi-main/`).  
4. `cd` into that folder and follow **Steps 3 – 5** above.

---

## Just need the three files?

```bash
curl -O https://raw.githubusercontent.com/ElodineOfficial/Gotchi/main/main.py
curl -O https://raw.githubusercontent.com/ElodineOfficial/Gotchi/main/needs_phrases.txt
curl -O https://raw.githubusercontent.com/ElodineOfficial/Gotchi/main/random_events.txt

pip install pytz
python main.py
```

*(Rename `main.py` if the actual filename in the repo differs.)*

---


### Enjoy!

If you hit a **File not found** or **permission** error, double‑check you’re inside the folder that contains **all three files** before running the script.
