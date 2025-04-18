import time
import random
import sys
import math
import threading
import queue
from datetime import datetime
import pytz

# --- Setup for line-based user input in a thread ---
user_input_queue = queue.Queue()

def input_thread():
    """
    Reads lines from stdin and places them into a queue
    so the main thread can be non-blocking.
    """
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        user_input_queue.put(line.strip())

# --- Utility functions for reading text files ---

def read_phrases(filename):
    """
    Reads lines from 'needs_phrases.txt' of the form:
       text|stat|delta
    e.g. 'I'm hungry|hunger|-1'
    Returns a list of tuples: [(text, stat, delta), ...]
    """
    p = []
    try:
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split("|")
                    if len(parts) == 3:
                        text = parts[0]
                        stat = parts[1]
                        try:
                            delta = float(parts[2])
                        except:
                            delta = 0
                        p.append((text, stat, delta))
                    else:
                        # If there's no pipe or it's malformed, just store raw text, no stat/delta
                        p.append((line, "", 0))
    except:
        pass
    return p

def read_events(filename):
    e = []
    try:
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    e.append(line)
    except:
        pass
    return e

def get_est_time():
    return datetime.now(pytz.timezone("US/Eastern"))

# --- Functions to help with updating the display ---

def generate_display_lines(
    msg, 
    hunger, 
    happiness, 
    energy, 
    weather, 
    mood, 
    day_time, 
    pet_sick,
    pet_away,
    clock_str
):
    """
    Generate the list of lines representing the "GUI" in the console.
    Returns a list of strings.
    """
    # Format numeric values
    h_str = "{:.2f}".format(hunger)
    ha_str = "{:.2f}".format(happiness)
    en_str = "{:.2f}".format(energy)

    lines = []
    lines.append(f"{clock_str} | Weather: {weather} | Mood: {mood} | {'Day' if day_time else 'Night'}")  # Use clock_str instead of time_str
    lines.append("   .----------------------.")

    if msg:
        # We might want to ensure it's not too wide for the box
        lines.append("   | " + msg + " |")
    else:
        lines.append("   |                    |")

    lines.append("   '------o---------------'")
    lines.append("          o")
    lines.append("           o")

    if not pet_away:
        # The pet face
        lines.append("            (\\_/)")
        if pet_sick:
            lines.append("            (x_x)")
        else:
            if happiness > 7:
                lines.append("            (^o^)")
            elif happiness < 3:
                lines.append("            (T_T)")
            else:
                lines.append("            (^_^)")
        
        # Holding a heart!
        lines.append("            />❤️ ")
    else:
        # Pet is away; display blank lines or a placeholder
        lines.append("")  # or "            ..."
        lines.append("")
        lines.append("")
        lines.append("")

    # Stats
    lines.append(f"Hunger: {h_str} | Happiness: {ha_str} | Energy: {en_str}")
    lines.append("[F]eed  [P]lay  [S]leep  [Q]uit")

    return lines

def partial_update_display(new_lines, old_lines):
    """
    Compare new_lines vs old_lines. For each line that differs,
    move the cursor there using ANSI escape codes, clear the line, and re-print it.
    Then move the cursor below the display so typed input doesn't collide.
    """
    max_lines = max(len(new_lines), len(old_lines))

    for i in range(max_lines):
        old_line = old_lines[i] if i < len(old_lines) else ""
        new_line = new_lines[i] if i < len(new_lines) else ""

        if new_line != old_line:
            # Move cursor to row i+1, column 1
            sys.stdout.write(f"\033[{i+1};1H")
            # Clear the entire line
            sys.stdout.write("\033[2K")
            # Print the new line
            sys.stdout.write(new_line)

    # After updating, move cursor below the last line, col 1
    sys.stdout.write(f"\033[{max_lines+1};1H")
    sys.stdout.flush()

def clear_screen():
    """
    Clear the screen and move the cursor to (1,1).
    """
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def main():
    # Start the input thread
    t = threading.Thread(target=input_thread, daemon=True)
    t.start()

    # Read any external text resources
    needs_phrases = read_phrases("needs_phrases.txt")
    random_events = read_events("random_events.txt")

    # Initialize pet stats
    hunger = 5.0
    happiness = 5.0
    energy = 5.0
    friendship = 5.0

    pet_sick = False
    pet_away = False
    away_start = 0
    away_used = 0
    last_away = 0

    # Timing/intervals
    last_input_time = time.time()
    last_needs_update = time.time()
    needs_interval = 120
    last_mood_check = -1
    mood = "content"
    weather = "Clear"
    last_weather_check = -1
    last_weather_period = -1
    day_time = True
    last_day_check = -1
    last_phrase_time = 0
    active_phrase_data = None  # Will hold (text, stat, delta) or None
    next_random_event_time = time.time() + random.randint(900, 1800)
    random_events_this_hour = 0
    last_event_hour = get_est_time().hour

    # A general "message" that shows up top
    msg = "           "
    msg_expiration_time = 0.0

    # We'll keep the last "state" to detect changes
    displayed_values = None
    # We'll also keep track of old display lines for partial updates
    old_display_lines = []

    # Function to set an ephemeral message for a certain duration
    def set_msg(new_msg, duration=30):
        nonlocal msg, msg_expiration_time
        msg = new_msg
        msg_expiration_time = time.time() + duration

    # Clear screen once at the start
    clear_screen()

    while True:
        now = time.time()
        est = get_est_time()  # <-- THIS LINE IS REQUIRED
        clock_str = est.strftime("%H:%M")  # Now safe to use 'est'
        current_hour = est.hour

        # If the ephemeral message expired, revert to a friend-hanging message
        if now > msg_expiration_time:
            msg = "Thanks for hanging out, friend!"

        # Reset random event counter on hour change
        if current_hour != last_event_hour:
            random_events_this_hour = 0
            last_event_hour = current_hour

        # If no input for a while, pet might wander off
        if not pet_away and (now - last_input_time) >= 300:
            # If we've never "gone away" or it's been a while, do it
            if away_used < 1 or (now - last_away) >= 600:
                pet_away = True
                away_start = now
                set_msg("Wandering off...", 30)
                last_away = now

        # Pet returns after a certain time away
        if pet_away and (now - away_start) >= 300:
            pet_away = False
            chance = random.random()
            if chance <= 0.8:
                # Pet returns feeling better in the lowest stat
                low_stat = min(
                    ("hunger", hunger),
                    ("happiness", happiness),
                    ("energy", energy),
                    key=lambda x: x[1]
                )[0]
                if low_stat == "hunger":
                    hunger = min(10.0, hunger + 1.5)
                elif low_stat == "happiness":
                    if not pet_sick:
                        happiness = min(10.0, happiness + 1.5)
                else:
                    energy = min(10.0, energy + 1.5)
                set_msg("Returned feeling better about life!", 30)
            else:
                # 20% chance something bad happens
                if random.random() < 0.2:
                    pet_sick = True
                    set_msg("Returned feeling icky...", 30)
                else:
                    set_msg("Scraped my knee...", 30)
            away_used += 1

        # If the pet is away but stats are zero, pet never returns
        if pet_away and (hunger <= 0 or happiness <= 0 or energy <= 0):
            print("\nYour ascii pet never returns.")
            sys.exit()

        # Periodic needs decrease (when pet not away)
        if int(now - last_needs_update) >= needs_interval and not pet_away:
            last_needs_update = now
            d = 0.5
            if pet_sick:
                d = 0.2
            if mood == "sad":
                happiness = max(0, happiness - 0.2)
            if day_time:
                hunger = max(0, hunger - d*1.2)
            else:
                hunger = max(0, hunger - d)
            if mood == "excited":
                energy = max(0, energy - d*1.5)
            elif day_time:
                energy = max(0, energy - d)
            else:
                energy = max(0, energy - d*1.2)
            if not pet_sick:
                happiness = max(0, happiness - d)

            # If any go to zero, pet dies
            if hunger == 0 or happiness == 0 or energy == 0:
                print("\nYour ascii pet has died.")
                sys.exit()

            # Friendship decays
            if friendship > 0:
                friendship = max(0, friendship - 0.1)
                if friendship == 0:
                    print("\nYour ascii pet has run away.")
                    sys.exit()

        # Check if it's day or night
        if current_hour != last_day_check:
            last_day_check = current_hour
            day_time = (6 <= current_hour < 18)

        # Weather check, switch in morning vs afternoon
        weather_period = 0 if current_hour < 12 else 1
        if weather_period != last_weather_period:
            last_weather_period = weather_period
            chance = random.random()
            if chance <= 0.8:
                weather = random.choice(["Clear", "Cloudy"])
            else:
                w = random.choice(["Rain", "Snow"])
                weather = w
                # chance pet gets sick
                if random.random() <= 0.2:
                    pet_sick = True

        # Mood check in 8-hour blocks
        mood_block = current_hour // 8
        if mood_block != last_mood_check:
            last_mood_check = mood_block
            if random.random() <= 0.5:
                mood = random.choice(["content", "sad", "excited"])

        # Cap stats at 10
        hunger = min(hunger, 10)
        happiness = min(happiness, 10)
        energy = min(energy, 10)

        # If hunger or energy is too high, random chance to become sick
        if hunger > 10 or energy > 9:
            if random.random() < 0.1:
                pet_sick = True

        # Random events
        if (
            random_events_this_hour < 2
            and time.time() >= next_random_event_time
            and not pet_away
        ):
            random_events_this_hour += 1
            next_random_event_time = time.time() + random.randint(1800, 3600)
            if random_events:
                ev = random.choice(random_events)
                set_msg(ev, 30)
                # Quick parse for plus/minus effect
                if "hunger+" in ev.lower():
                    hunger = min(10, hunger + 1)
                elif "hunger-" in ev.lower():
                    hunger = max(0, hunger - 1)
                elif "happy+" in ev.lower():
                    if not pet_sick:
                        happiness = min(10, happiness + 1)
                elif "happy-" in ev.lower():
                    happiness = max(0, happiness - 1)
                elif "energy+" in ev.lower():
                    energy = min(10, energy + 1)
                elif "energy-" in ev.lower():
                    energy = max(0, energy - 1)

                if hunger == 0 or happiness == 0 or energy == 0:
                    print("\nYour ascii pet has died.")
                    sys.exit()

        # Possibly spawn a needs phrase (only if pet isn't sick or away, 
        # and we don't already have one active)
        if (
            not pet_sick 
            and not pet_away 
            and needs_phrases 
            and random.random() < 0.01 
            and not active_phrase_data
        ):
            active_phrase_data = random.choice(needs_phrases)
            text, stat, delta = active_phrase_data
            last_phrase_time = time.time()
            # Show the phrase text for up to 120s (so user can see it)
            set_msg(text, 120)

        # Clear the active phrase if it's too old
        if active_phrase_data and (time.time() - last_phrase_time) > 120:
            text, stat, delta = active_phrase_data
            if msg == text:
                msg = "I wonder what we're doing next!"
            active_phrase_data = None

        # Process user input
        if not user_input_queue.empty():
            inp = user_input_queue.get()
            last_input_time = time.time()

            if inp.lower() == "q":
                print("\nExiting.")
                sys.exit()

            elif inp.lower() == "f" and not pet_away:
                # Normal feeding logic
                hunger = min(10, hunger + 1)
                energy = max(0, energy - 0.25)
                # chance to cure sickness by feeding
                if pet_sick and random.random() < 0.45:
                    pet_sick = False
                if hunger == 0 or energy == 0:
                    print("\nYour ascii pet has died.")
                    sys.exit()
                if (time.time() - last_needs_update) < 10 and friendship < 10:
                    friendship = min(10, friendship + 0.2)
                set_msg("Eating...", 30)

                # Check if there's an active phrase about 'hunger'
                if active_phrase_data:
                    text, stat, delta = active_phrase_data
                    if stat.lower() == "hunger":
                        # We interpret delta as how “negative” the pet is, so fulfilling
                        # the need means increasing that stat by -delta (subtracting a negative).
                        hunger = min(10, hunger - delta)
                        set_msg("Thank you for feeding me!", 30)
                        active_phrase_data = None

            elif inp.lower() == "p" and not pet_away:
                # Normal playing logic
                if not pet_sick:
                    happiness = min(10, happiness + 1)
                energy = max(0, energy - 0.25)
                if happiness == 0 or energy == 0:
                    print("\nYour ascii pet has died.")
                    sys.exit()
                if (time.time() - last_needs_update) < 10 and friendship < 10:
                    friendship = min(10, friendship + 0.2)
                set_msg("Zoomies!!!", 30)

                # Check if there's an active phrase about 'happiness'
                if active_phrase_data:
                    text, stat, delta = active_phrase_data
                    if stat.lower() == "happiness":
                        happiness = min(10, happiness - delta)
                        set_msg("Thank you for playing with me!", 30)
                        active_phrase_data = None

            elif inp.lower() == "s" and not pet_away:
                # Normal sleeping logic
                energy = min(10, energy + 1)
                hunger = max(0, hunger - 0.25)
                if energy == 0 or hunger == 0:
                    print("\nYour ascii pet has died.")
                    sys.exit()
                if (time.time() - last_needs_update) < 10 and friendship < 10:
                    friendship = min(10, friendship + 0.2)
                set_msg("Sleeping...", 30)

                # Check if there's an active phrase about 'energy'
                if active_phrase_data:
                    text, stat, delta = active_phrase_data
                    if stat.lower() == "energy":
                        energy = min(10, energy - delta)
                        set_msg("Thank you for letting me rest!", 30)
                        active_phrase_data = None

            else:
                # Catch-all for any typed text
                set_msg(inp, 30)

        # Check if pet died from stats going to zero
        if hunger <= 0 or happiness <= 0 or energy <= 0:
            print("\nYour ascii pet has died.")
            sys.exit()

        # Decide if anything has changed enough to re-draw
        current_display = (
            weather,
            mood,
            day_time,
            round(hunger, 2),
            round(happiness, 2),
            round(energy, 2),
            msg,
            pet_sick,
            pet_away
        )

        if current_display != displayed_values:
            # Build the new lines
            new_display_lines = generate_display_lines(
                msg,
                hunger,
                happiness,
                energy,
                weather,
                mood,
                day_time,
                pet_sick,
                pet_away,
                clock_str
            )
            # Update only changed lines
            partial_update_display(new_display_lines, old_display_lines)

            old_display_lines = new_display_lines
            displayed_values = current_display

        time.sleep(0.1)

if __name__ == "__main__":
    main()
