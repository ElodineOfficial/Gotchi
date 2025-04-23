# **Gotchi Program Overview**

## **1. Setup & Input Handling**

- **Background input thread** reads your keystrokes into a queue so the main loop never blocks.

- **File readers** load “needs” phrases (CSV) and random events (plain text) that the pet may display.


## **2. Initialization & Hidden State**

- **Visible stats** start at 5.0 each:

  - Hunger

  - Happiness

  - Energy

- **Hidden stat**: Friendship (decays slowly; if it hits 0, your pet runs away).

- **Flags & timers** track sickness, “away” status, message expirations, next random event, clock logic, etc.


## **3. Console Interface (What You See)**

HH:MM | Weather: Clear | Mood: content | Day

   .----------------------.

   |   Message here…     |

   '------o---------------'

          o

           o

            (\\\_/)

            (^\_^)   ← face changes by happiness or sickness

            />❤️ 

Hunger: 5.00 | Happiness: 5.00 | Energy: 5.00

\[F]eed  \[P]lay  \[S]leep  \[Q]uit

- **Header** shows real clock, weather, mood, day/night.

- **Message box** displays ephemeral messages or needs.

- **ASCII pet** face and heart icon reflect mood/sickness.

- **Stats line** with two‐decimal precision.

- **Commands**: F = feed, P = play, S = sleep, Q = quit.


## **4. Core Simulation Loop (**`step`**)**

1. **Advance time** by one “step.” Every 120 steps ≈ one needs‐interval.

2. **Decay stats** every interval (modified by day/night, mood, sickness).

3. **Friendship decay** of 0.1 per interval; hitting zero ⇒ run away.

4. **Death** if hunger, happiness, or energy reaches 0.

5. **Away logic**:

   - No input for 300 steps ⇒ pet wanders off.

   - Returns after 300 more steps with random boosts, knee scrapes, or sickness.

6. **Random events**:

   - In real‐time mode, up to two per hour.

   - Manual trigger flag for step mode.

   - Parses text for “hunger+”, “happy–”, etc., to adjust stats.

   - Sick Mechanics:

     1. Due to improper care, or bad weather, a Gotchi may become sick, it is unable to re-coop happiness at the same rate during this time.

7. **Needs phrases** (\~1% chance each step) pop up for 120 steps and await the matching action.

   - Matching a phrase to a specific action IE: ‘I’m hungry’ + \[F]eed = bonuses to happiness


## **5. Player Actions**

- **feed()**

  - +1 hunger, −0.25 energy, 45% cure chance if sick, +0.2 friendship.

  - Clears any active “hunger” need phrase.

  - Overfeeding may lead to a pet becoming sick

- **play()**

  - +1 happiness (if not sick), −0.25 energy, +0.2 friendship.

  - Clears “happiness” need phrase.

- **sleep()**

  - +1 energy, −0.25 hunger, +0.2 friendship.

  - Clears “energy” need phrase.


## **6. Real-Time Mode**

- **Clock mapping**: wall‐clock seconds → simulation steps (maintains a 120-step interval).

- **Weather updates** twice daily (clear/cloudy vs. rain/snow + sickness risk).

- **Mood updates** every 8 real hours (randomly “content,” “sad,” or “excited”).

- **Random events** scheduled 30–60 minutes apart, max twice per hour.

- **Efficient redraw** at ≤10 FPS via ANSI cursor moves when state changes.

