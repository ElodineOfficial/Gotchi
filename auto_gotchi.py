#!/usr/bin/env python3
"""
gotchi_auto_player.py  –  v2.2  (2025‑07‑31)
--------------------------------------------

* This is an alternative to the collab space for a local run with automatic graphs
* Dual‑run harness for gotchi_beta.py
* GPT‑o driver, logs & graph [idea stolen from McCardle, many thanks!]
* **NEW in v2.2**:
    • Robust death detection → immediate second run
    • Flush input queue between runs
    • Still cross‑platform (msvcrt on Windows, select() elsewhere)
"""

from __future__ import annotations

import csv
import json
import os
import queue
import re
import select
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

import matplotlib.pyplot as plt  # type: ignore
import openai
from dotenv import load_dotenv  # type: ignore

# ───────────────────────────────────────────────────────────────────────────
# 1.  CONFIG
# ───────────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.resolve()
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise EnvironmentError("Set OPENAI_API_KEY (env or .env file).")

MODEL        = os.getenv("OPENAI_MODEL", "o3")
TEMPERATURE  = float(os.getenv("OPENAI_TEMPERATURE", "1"))
CALL_PERIOD  = 120          # seconds between GPT calls
MAX_RUNS     = 2

REGEX_CMD  = re.compile(r"\[?\s*([FPSQfpsq])\s*\]?", re.I)
REGEX_DEAD = re.compile(r"ascii pet has died", re.I)

# ───────────────────────────────────────────────────────────────────────────
# 2.  IMPORT GAME
# ───────────────────────────────────────────────────────────────────────────
try:
    from gotchi_beta import Gotchi, user_input_queue  # type: ignore
except ModuleNotFoundError:
    print("✖ Cannot import gotchi_beta.py – place it alongside this file.",
          file=sys.stderr)
    raise

# ───────────────────────────────────────────────────────────────────────────
# 3.  GLOBAL STATE (spans both runs)
# ───────────────────────────────────────────────────────────────────────────
stat_rows: list[dict[str, float | str]] = []
stats_lock = threading.Lock()
summaries: list[str] = []

# ───────────────────────────────────────────────────────────────────────────
# 4.  HELPERS
# ───────────────────────────────────────────────────────────────────────────
def timestamp() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def capture_screen(pet: Gotchi) -> str:
    return "\n".join(pet.generate_display_lines())


def parse_command(text: str) -> str | None:
    m = REGEX_CMD.search(text or "")
    return m.group(1).lower() if m else None


def enqueue_command(cmd: str) -> None:
    user_input_queue.put(cmd)


def flush_input_queue() -> None:
    """Drain user_input_queue completely."""
    try:
        while True:
            user_input_queue.get_nowait()
    except queue.Empty:
        pass


def log_stats(pet: Gotchi, cmd: str) -> None:
    with stats_lock:
        stat_rows.append(
            {
                "timestamp": timestamp(),
                "command": cmd.upper(),
                "hunger":    round(pet.hunger, 3),
                "happiness": round(pet.happiness, 3),
                "energy":    round(pet.energy, 3),
                "total":     round(pet.hunger + pet.happiness + pet.energy, 3),
            }
        )


def draw_plot(path: Path, rows) -> None:
    if not rows:
        return
    turns  = list(range(len(rows)))
    totals = [r["total"] for r in rows]           # type: ignore[index]

    plt.style.use("dark_background")
    plt.rcParams["font.family"] = "monospace"
    fig, ax = plt.subplots(figsize=(10, 5), facecolor="black")
    ax.set_facecolor("black")
    ax.plot(turns, totals, color="orange",
            linewidth=2, marker="o", markersize=4,
            markerfacecolor="orange", markeredgecolor="orange")
    ax.set_title("Hunger + Happiness + Energy over Time", pad=12)
    ax.set_xlabel("Turn (#)")
    ax.set_ylabel("Total Stat Value")
    ax.grid(color="gray", linestyle="--", linewidth=0.4, alpha=0.4)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)

# ───────────────────────────────────────────────────────────────────────────
# 5.  DEATH DETECTION
# ───────────────────────────────────────────────────────────────────────────
def is_pet_dead(pet: Gotchi, screen: str | None = None) -> bool:
    """
    Returns True as soon as the pet dies.  Checks three things:
      1) The usual screen‑text regex (fast, language‑agnostic).
      2) Attribute flags on the Gotchi instance (alive / dead).
      3) A callable `is_alive()` method, if present.
    """
    screen = screen or ""
    if REGEX_DEAD.search(screen):
        return True

    if hasattr(pet, "alive") and getattr(pet, "alive") is False:
        return True
    if hasattr(pet, "dead") and getattr(pet, "dead") is True:
        return True
    if callable(getattr(pet, "is_alive", None)):
        try:
            if pet.is_alive() is False:          # type: ignore[arg-type]
                return True
        except Exception:  # noqa: BLE001
            pass
    return False

# ───────────────────────────────────────────────────────────────────────────
# 6.  GPT‑DRIVER THREAD
# ───────────────────────────────────────────────────────────────────────────
def gpt_loop(
    pet: Gotchi,
    stop_event: threading.Event,
    pet_dead_event: threading.Event,
    conversation: list[dict[str, str]],
) -> None:
    while not stop_event.is_set() and not pet_dead_event.is_set():
        tic = time.time()

        screen = capture_screen(pet)
        if is_pet_dead(pet, screen):
            pet_dead_event.set()
            break

        conversation.append({"role": "user", "content": screen})

        try:
            resp = openai.ChatCompletion.create(
                model=MODEL,
                messages=conversation,
                temperature=TEMPERATURE,
                timeout=90,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[GPT] OpenAI error – {exc}", file=sys.stderr)
            time.sleep(10)
            continue

        ai_text = resp.choices[0].message.content.strip()
        conversation.append({"role": "assistant", "content": ai_text})
        cmd = parse_command(ai_text)

        if cmd:
            enqueue_command(cmd)
            log_stats(pet, cmd)
            if cmd == "q":
                stop_event.set()
        else:
            print(f"[GPT] Could not parse command from: {ai_text!r}",
                  file=sys.stderr)

        # throttle to CALL_PERIOD
        elapsed = time.time() - tic
        sleep_for = max(0, CALL_PERIOD - elapsed)
        for _ in range(int(sleep_for)):
            if stop_event.is_set() or pet_dead_event.is_set():
                break
            time.sleep(1)

# ───────────────────────────────────────────────────────────────────────────
# 7.  SUMMARISATION
# ───────────────────────────────────────────────────────────────────────────
def summarise_run(conv: list[dict[str, str]], run_no: int) -> str:
    prompt = [
        {
            "role": "system",
            "content": (
                "You are an analyst for this run. "
                "Provide a concise (≤150 words) retrospective of this event—"
                "strategy, key points and advice for the next run."
            ),
        },
        *conv[-40:],
        {"role": "user", "content": "Please summarise this run now."},
    ]
    try:
        resp = openai.ChatCompletion.create(
            model=MODEL,
            messages=prompt,
            temperature=1,
            timeout=90,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:  # noqa: BLE001
        return f"[Summary generation failed: {exc}]"

# ───────────────────────────────────────────────────────────────────────────
# 8.  NON‑BLOCKING STDIN (cross‑platform)
# ───────────────────────────────────────────────────────────────────────────
def poll_stdin() -> str | None:
    """
    Returns a lower‑case single character (f/p/s/q) if one is waiting,
    otherwise None – without blocking.
    """
    if os.name == "nt":
        import msvcrt  # type: ignore
        if msvcrt.kbhit():
            ch = msvcrt.getwch()
            if ch in ("\r", "\n"):
                return None
            return ch.lower()
    else:
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.readline().strip().lower()
    return None

# ───────────────────────────────────────────────────────────────────────────
# 9.  ONE RUN
# ───────────────────────────────────────────────────────────────────────────
def run_once(run_no: int) -> None:
    print(f"\n—— RUN {run_no}/{MAX_RUNS} ———————————————", file=sys.stderr)

    stop_event     = threading.Event()
    pet_dead_event = threading.Event()
    conversation: list[dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "You are caring for this simulation.\n"
                "At each turn you see the ENTIRE screen and must choose exactly one "
                "action:\n\n"
                "  [F]eed   [P]lay   [S]leep   [Q]uit\n\n"
                "Reply with JUST that letter."
            ),
        }
    ]

    flush_input_queue()                     # clean slate 🔄
    pet = Gotchi()
    pet_thread = threading.Thread(target=pet.realtime, daemon=True)
    gpt_thread = threading.Thread(
        target=gpt_loop,
        args=(pet, stop_event, pet_dead_event, conversation),
        daemon=True,
    )
    pet_thread.start()
    gpt_thread.start()

    try:
        while not stop_event.is_set() and not pet_dead_event.is_set():
            # operator override
            key = poll_stdin()
            if key:
                if key in {"f", "p", "s", "q"}:
                    enqueue_command(key)
                    log_stats(pet, key)
                    if key == "q":
                        stop_event.set()
                else:
                    user_input_queue.put(key)

            # independent death check (screen or attribute)
            if is_pet_dead(pet, capture_screen(pet)):
                pet_dead_event.set()

            time.sleep(0.05)

    except KeyboardInterrupt:
        stop_event.set()

    # tidy‑up this run
    stop_event.set()
    pet_dead_event.set()
    pet_thread.join(timeout=5)
    gpt_thread.join(timeout=5)

    if pet_dead_event.is_set():
        summary = summarise_run(conversation, run_no)
        summaries.append(summary)
        print(f"\n—— Summary of run {run_no} ——\n{summary}\n", file=sys.stderr)
    else:
        summaries.append("Run ended by explicit quit (no summary).")

    print(f"Run {run_no} finished.\n", file=sys.stderr)
    time.sleep(1)

# ───────────────────────────────────────────────────────────────────────────
# 10.  FINAL SHUTDOWN
# ───────────────────────────────────────────────────────────────────────────
def final_shutdown() -> None:
    ts = int(time.time())
    csv_path  = LOG_DIR / f"gotchi_stats_{ts}.csv"
    json_path = LOG_DIR / f"summaries_{ts}.json"
    png_path  = LOG_DIR / f"stats_{ts}.png"

    with stats_lock:
        if stat_rows:
            with csv_path.open("w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=stat_rows[0].keys())
                w.writeheader()
                w.writerows(stat_rows)
    with json_path.open("w") as f:
        json.dump({"summaries": summaries}, f, indent=2)
    draw_plot(png_path, stat_rows)

    print(f"\n ➜ CSV log saved to  {csv_path}",  file=sys.stderr)
    print(f" ➜ Summaries saved to {json_path}", file=sys.stderr)
    print(f" ➜ Graph     saved to {png_path}", file=sys.stderr)
    print("Good‑bye!", file=sys.stderr)
    sys.exit(0)

# ───────────────────────────────────────────────────────────────────────────
# 11.  MAIN
# ───────────────────────────────────────────────────────────────────────────
def main() -> None:
    for rn in range(1, MAX_RUNS + 1):
        run_once(rn)
    final_shutdown()


if __name__ == "__main__":
    print("\nLaunching automated GPT tester (dual‑run)…  CTRL‑C to stop.\n")
    main()
