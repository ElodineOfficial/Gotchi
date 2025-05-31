import csv
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
    with open(filename, newline='', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='|')
        rows = []
        for row in reader:
            if row and len(row) == 3:
                rows.append((row[0], row[1], float(row[2])))
        return rows

def read_events(filename):
    with open(filename, encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def get_est_time():
    return datetime.now(pytz.timezone("US/Eastern"))

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

    pet = Gotchi()
    pet.realtime()

class Gotchi:
    def __init__(self, needs_phrases=None, random_events=None):
        if needs_phrases is None:
            needs_phrases = read_phrases("needs_phrases.txt")
        self.needs_phrases = needs_phrases
        if random_events is None:
            random_events = read_events("random_events.txt")
        self.random_events = random_events
        # Initialize pet stats
        self.hunger = 5.0
        self.happiness = 5.0
        self.energy = 5.0
        self.friendship = 5.0

        self.pet_sick = False
        self.pet_away = False
        self.away_start = 0
        self.away_used = 0
        self.last_away = 0

        # Timing/intervals
        self.current_time = 0  # offset from initialization, "seconds" or "steps"
        self.last_input_time = self.current_time
        self.last_needs_update = self.current_time

        self.needs_interval = 120
        self.last_mood_check = -1
        self.mood = "content"
        self.weather = "Clear"
        self.last_weather_check = -1
        self.last_weather_period = -1
        self.day_time = True
        self.last_day_check = -1
        self.last_phrase_time = self.current_time
        self.active_phrase_data = None  # Will hold (text, stat, delta) or None
        self.next_random_event_time = self.current_time + random.randint(900, 1800)
        self.random_events_this_hour = 0
        self.last_event_hour = 0

        # A general "message" that shows up top
        self.msg = "           "
        self.msg_expiration_time = 0.0

        # We'll keep the last "state" to detect changes
        self.displayed_values = None
        # We'll also keep track of old display lines for partial updates
        self.old_display_lines = []

        # Clock time for display
        self.clock_str = "00:00"
        self.current_hour = 0
        self.last_clock_update = self.current_time # for advancing "pet clock time" in non-realtime steps

    # Function to set an ephemeral message for a certain duration
    def set_msg(self, new_msg, duration=30):
        self.msg = new_msg
        self.msg_expiration_time = self.current_time + duration

    def generate_display_lines(self):
        """
        Generate the list of lines representing the "GUI" in the console.
        Returns a list of strings.
        """
        # Format numeric values
        h_str = "{:.2f}".format(self.hunger)
        ha_str = "{:.2f}".format(self.happiness)
        en_str = "{:.2f}".format(self.energy)

        lines = []
        lines.append(f"{self.clock_str} | Weather: {self.weather} | Mood: {self.mood} | {'Day' if self.day_time else 'Night'}")
        lines.append("   .----------------------.")

        if self.msg:
            # We might want to ensure it's not too wide for the box
            lines.append("   | " + self.msg + " |")
        else:
            lines.append("   |                    |")

        lines.append("   '------o---------------'")
        lines.append("          o")
        lines.append("           o")

        if not self.pet_away:
            # The pet face
            lines.append("            (\\_/)")
            if self.pet_sick:
                lines.append("            (x_x)")
            else:
                if self.happiness > 7:
                    lines.append("            (^o^)")
                elif self.happiness < 3:
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

    def draw(self):
        """print to terminal"""
        for l in self.generate_display_lines():
            print(l)

    def step(self, n=None, real_time=False):
        """
        Advance the simulation by one step (or n steps)
        This represents a single unit of simulation time
        """
        # slightly recursive method: built-in loop for multiple steps
        if n is not None:
            for i in range(n):
                result = self.step(real_time=real_time)
                if result:
                    return result
            return

        # single-step behavior: increment time
        self.current_time += 1

        # advance pet time
        if not real_time and (self.current_time - self.last_clock_update) >= 60:
            self.last_clock_update = self.current_time
            hour_s, minute_s = self.clock_str.split(":")
            minute = int(minute_s) + (self.needs_interval // 60)
            hour = int(hour_s)
            if minute >= 60:
                minute -= 60
                hour += 1
                if hour > 12:
                    hour = 1
                    self.day_time = not self.day_time
            self.clock_str = f"{hour:02d}:{minute:02d}"

        # If the ephemeral message expired, revert to a friend-hanging message
        if self.current_time > self.msg_expiration_time:
            self.msg = "Thanks for hanging out, friend!"

        # If no input for a while, pet might wander off
        if not self.pet_away and (self.current_time - self.last_input_time) >= 300:
            # If we've never "gone away" or it's been a while, do it
            if self.away_used < 1 or (self.current_time - self.last_away) >= 600:
                self.pet_away = True
                self.away_start = self.current_time
                self.set_msg("Wandering off...", 30)
                self.last_away = self.current_time

        # Pet returns after a certain time away
        if self.pet_away and (self.current_time - self.away_start) >= 300:
            self.pet_away = False
            chance = random.random()
            if chance <= 0.8:
                # Pet returns feeling better in the lowest stat
                low_stat = min(
                    ("hunger", self.hunger),
                    ("happiness", self.happiness),
                    ("energy", self.energy),
                    key=lambda x: x[1]
                )[0]
                if low_stat == "hunger":
                    self.hunger = min(10.0, self.hunger + 1.5)
                elif low_stat == "happiness":
                    if not self.pet_sick:
                        self.happiness = min(10.0, self.happiness + 1.5)
                else:
                    self.energy = min(10.0, self.energy + 1.5)
                self.set_msg("Returned feeling better about life!", 30)
            else:
                # 20% chance something bad happens
                if random.random() < 0.2:
                    self.pet_sick = True
                    self.set_msg("Returned feeling icky...", 30)
                else:
                    self.set_msg("Scraped my knee...", 30)
            self.away_used += 1

        # If the pet is away but stats are zero, pet never returns
        if self.pet_away and (self.hunger <= 0 or self.happiness <= 0 or self.energy <= 0):
            return "Your ascii pet never returns."

        # Periodic needs decrease (when pet not away)
        if (self.current_time - self.last_needs_update) >= self.needs_interval and not self.pet_away:
            self.last_needs_update = self.current_time
            d = 0.5
            if self.pet_sick:
                d = 0.2
            if self.mood == "sad":
                self.happiness = max(0, self.happiness - 0.2)
            if self.day_time:
                self.hunger = max(0, self.hunger - d*1.2)
            else:
                self.hunger = max(0, self.hunger - d)
            if self.mood == "excited":
                self.energy = max(0, self.energy - d*1.5)
            elif self.day_time:
                self.energy = max(0, self.energy - d)
            else:
                self.energy = max(0, self.energy - d*1.2)
            if not self.pet_sick:
                self.happiness = max(0, self.happiness - d)

            # If any go to zero, pet dies
            if self.hunger == 0 or self.happiness == 0 or self.energy == 0:
                return "Your ascii pet has died."

            # Friendship decays
            if self.friendship > 0:
                self.friendship = max(0, self.friendship - 0.1)
                if self.friendship == 0:
                    return "Your ascii pet has run away."

        # Random events - only in step mode if specifically triggered
        if hasattr(self, 'trigger_random_event') and self.trigger_random_event:
            self.trigger_random_event = False
            if self.random_events:
                ev = random.choice(self.random_events)
                self.set_msg(ev, 30)
                # Quick parse for plus/minus effect
                if "hunger+" in ev.lower():
                    self.hunger = min(10, self.hunger + 1)
                elif "hunger-" in ev.lower():
                    self.hunger = max(0, self.hunger - 1)
                elif "happy+" in ev.lower():
                    if not self.pet_sick:
                        self.happiness = min(10, self.happiness + 1)
                elif "happy-" in ev.lower():
                    self.happiness = max(0, self.happiness - 1)
                elif "energy+" in ev.lower():
                    self.energy = min(10, self.energy + 1)
                elif "energy-" in ev.lower():
                    self.energy = max(0, self.energy - 1)

                if self.hunger == 0 or self.happiness == 0 or self.energy == 0:
                    return "Your ascii pet has died."

        # Possibly spawn a needs phrase (only if pet isn't sick or away,
        # and we don't already have one active)
        if (
            not self.pet_sick
            and not self.pet_away
            and self.needs_phrases
            and random.random() < 0.01
            and not self.active_phrase_data
        ):
            self.active_phrase_data = random.choice(self.needs_phrases)
            text, stat, delta = self.active_phrase_data
            self.last_phrase_time = self.current_time
            # Show the phrase text for up to 120s (so user can see it)
            self.set_msg(text, 120)

        # Clear the active phrase if it's too old
        if self.active_phrase_data and (self.current_time - self.last_phrase_time) > 120:
            text, stat, delta = self.active_phrase_data
            if self.msg == text:
                self.msg = "I wonder what we're doing next!"
            self.active_phrase_data = None

        # Cap stats at 10
        self.hunger = min(self.hunger, 10)
        self.happiness = min(self.happiness, 10)
        self.energy = min(self.energy, 10)

        # If hunger or energy is too high, random chance to become sick
        if self.hunger > 10 or self.energy > 9:
            if random.random() < 0.1:
                self.pet_sick = True

        # Check if pet died from stats going to zero
        if self.hunger <= 0 or self.happiness <= 0 or self.energy <= 0:
            return "Your ascii pet has died."

        return None  # No special status to report

    def sleep(self):
        # Normal sleeping logic
        self.energy = min(10, self.energy + 1)
        self.hunger = max(0, self.hunger - 0.25)
        if self.energy == 0 or self.hunger == 0:
            return "Your ascii pet has died."
        
        # In step simulation, we don't need real time comparison
        if self.friendship < 10:
            self.friendship = min(10, self.friendship + 0.2)
            
        self.set_msg("Sleeping...", 30)

        # Check if there's an active phrase about 'energy'
        if self.active_phrase_data:
            text, stat, delta = self.active_phrase_data
            if stat.lower() == "energy":
                self.energy = min(10, self.energy - delta)
                self.set_msg("Thank you for letting me rest!", 30)
                self.active_phrase_data = None
        
        return None

    def feed(self):
        # Normal feeding logic
        self.hunger = min(10, self.hunger + 1)
        self.energy = max(0, self.energy - 0.25)
        # chance to cure sickness by feeding
        if self.pet_sick and random.random() < 0.45:
            self.pet_sick = False
        if self.hunger == 0 or self.energy == 0:
            return "Your ascii pet has died."
            
        # In step simulation, we don't need real time comparison
        if self.friendship < 10:
            self.friendship = min(10, self.friendship + 0.2)
            
        self.set_msg("Eating...", 30)

        # Check if there's an active phrase about 'hunger'
        if self.active_phrase_data:
            text, stat, delta = self.active_phrase_data
            if stat.lower() == "hunger":
                # We interpret delta as how "negative" the pet is, so fulfilling
                # the need means increasing that stat by -delta (subtracting a negative).
                self.hunger = min(10, self.hunger - delta)
                self.set_msg("Thank you for feeding me!", 30)
                self.active_phrase_data = None
                
        return None

    def play(self):
        # Normal playing logic
        if not self.pet_sick:
            self.happiness = min(10, self.happiness + 1)
        self.energy = max(0, self.energy - 0.25)
        if self.happiness == 0 or self.energy == 0:
            return "Your ascii pet has died."
            
        # In step simulation, we don't need real time comparison
        if self.friendship < 10:
            self.friendship = min(10, self.friendship + 0.2)
            
        self.set_msg("Zoomies!!!", 30)

        # Check if there's an active phrase about 'happiness'
        if self.active_phrase_data:
            text, stat, delta = self.active_phrase_data
            if stat.lower() == "happiness":
                self.happiness = min(10, self.happiness - delta)
                self.set_msg("Thank you for playing with me!", 30)
                self.active_phrase_data = None
                
        return None

    def update_time_from_realtime(self, wall_time):
        """Calculate simulation steps based on wall time"""
        # This is a helper function for realtime() to convert wall time to sim time
        return int(wall_time / self.needs_interval * 120)  # 120 steps per needs_interval

    def realtime(self):
        """Run the pet simulation in real-time with terminal display"""
        # Clear screen once at the start
        clear_screen()
        
        # Initialize real-time tracking variables
        start_time = time.time()
        last_step_time = start_time
        last_display_time = start_time

        while True:
            # Get current wall-clock time
            now = time.time()
            est = get_est_time()
            self.clock_str = est.strftime("%H:%M")
            self.current_hour = est.hour

            # Convert elapsed real time to simulation steps
            elapsed_sim_time = self.update_time_from_realtime(now - start_time)
            steps_to_run = elapsed_sim_time - self.current_time
            
            # Reset random event counter on hour change
            if self.current_hour != self.last_event_hour:
                self.random_events_this_hour = 0
                self.last_event_hour = self.current_hour

            # Check if it's day or night based on real time
            if self.current_hour != self.last_day_check:
                self.last_day_check = self.current_hour
                self.day_time = (6 <= self.current_hour < 18)

            # Weather check, switch in morning vs afternoon based on real time
            weather_period = 0 if self.current_hour < 12 else 1
            if weather_period != self.last_weather_period:
                self.last_weather_period = weather_period
                chance = random.random()
                if chance <= 0.8:
                    self.weather = random.choice(["Clear", "Cloudy"])
                else:
                    w = random.choice(["Rain", "Snow"])
                    self.weather = w
                    # chance pet gets sick
                    if random.random() <= 0.2:
                        self.pet_sick = True

            # Mood check in 8-hour blocks based on real time
            mood_block = self.current_hour // 8
            if mood_block != self.last_mood_check:
                self.last_mood_check = mood_block
                if random.random() <= 0.5:
                    self.mood = random.choice(["content", "sad", "excited"])
                    
            # Random events check (only in real-time mode)
            if (
                self.random_events_this_hour < 2
                and now >= (start_time + self.next_random_event_time)
                and not self.pet_away
            ):
                self.random_events_this_hour += 1
                self.next_random_event_time = now + random.randint(1800, 3600) - start_time
                self.trigger_random_event = True

            # Run simulation steps if needed
            if steps_to_run > 0:
                for _ in range(steps_to_run):
                    status = self.step(real_time=True)
                    if status:
                        print(status)
                        return

            # Process user input
            if not user_input_queue.empty():
                inp = user_input_queue.get()
                self.last_input_time = self.current_time

                if inp.lower() == "q":
                    print("\nExiting.")
                    return

                elif inp.lower() == "f" and not self.pet_away:
                    status = self.feed()
                    if status:
                        print(status)
                        return

                elif inp.lower() == "p" and not self.pet_away:
                    status = self.play()
                    if status:
                        print(status)
                        return

                elif inp.lower() == "s" and not self.pet_away:
                    status = self.sleep()
                    if status:
                        print(status)
                        return

                else:
                    # Catch-all for any typed text
                    self.set_msg(inp, 30)

            # Update display if needed - limit to 10fps for efficiency 
            if now - last_display_time >= 0.1:
                last_display_time = now
                
                # Decide if anything has changed enough to re-draw
                current_display = (
                    self.weather,
                    self.mood,
                    self.day_time,
                    round(self.hunger, 2),
                    round(self.happiness, 2),
                    round(self.energy, 2),
                    self.msg,
                    self.pet_sick,
                    self.pet_away
                )

                if current_display != self.displayed_values:
                    new_display_lines = self.generate_display_lines()
                    partial_update_display(new_display_lines, self.old_display_lines)
                    self.old_display_lines = new_display_lines
                    self.displayed_values = current_display

            time.sleep(0.1)

if __name__ == "__main__":
    main()
