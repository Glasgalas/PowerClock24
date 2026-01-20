import tkinter as tk
from PIL import Image, ImageDraw, ImageTk
from math import sin, cos, radians
from datetime import datetime
import requests

# ================== НАЛАШТУВАННЯ ==================
SIZE = 200
GAP = 20
WIDTH = SIZE * 2 + GAP
HEIGHT = SIZE

C = SIZE // 2

R_OUT = 73
R_IN = 42

SECTORS = 12
STEP = 360 / SECTORS
HALF = STEP / 2

GREEN = (80, 180, 90, 190)
RED   = (220, 70, 70, 190)

BG_PADDING = 2

UPDATE_HANDS_MS = 60_000
UPDATE_DATA_MS  = 15 * 60_000

AM_TEMPLATE = "powerClock-AM.png"
PM_TEMPLATE = "powerClock-PM.png"

JSON_URL = "https://raw.githubusercontent.com/Baskerville42/outage-data-ua/main/data/kyiv-region.json"

# ================== КІЛЬЦЕВИЙ СЕКТОР ==================
def draw_ring_sector(draw, start_deg, end_deg, color):
    points = []

    for a in range(int(start_deg), int(end_deg) + 1):
        r = radians(a)
        points.append((C + R_OUT * cos(r), C + R_OUT * sin(r)))

    for a in range(int(end_deg), int(start_deg) - 1, -1):
        r = radians(a)
        points.append((C + R_IN * cos(r), C + R_IN * sin(r)))

    draw.polygon(points, fill=color)

# ================== ЦИФЕРБЛАТ ==================
def draw_dial(hours_range, template_path, schedule):
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    for hour in hours_range:
        state = schedule.get(hour, "yes")
        sector = (hour - 1) % 12

        start = -90 + sector * STEP
        mid   = start + HALF
        end   = start + STEP

        if state == "yes":
            draw_ring_sector(d, start, end, GREEN)
        elif state == "no":
            draw_ring_sector(d, start, end, RED)
        elif state == "first":
            draw_ring_sector(d, start, mid, RED)
            draw_ring_sector(d, mid, end, GREEN)
        elif state == "second":
            draw_ring_sector(d, start, mid, GREEN)
            draw_ring_sector(d, mid, end, RED)

    template = Image.open(template_path).convert("RGBA")
    template = template.resize((SIZE, SIZE), Image.LANCZOS)

    return Image.alpha_composite(img, template)

# ================== СТВОРЕННЯ СТРІЛКИ ==================
def create_hand(length, width, color=(0, 0, 0, 255)):
    size = length * 2
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    cx = cy = size // 2

    d.rectangle(
        [
            cx - width // 2,
            cy - length,
            cx + width // 2,
            cy
        ],
        fill=color
    )

    d.ellipse(
        [cx - 5, cy - 5, cx + 5, cy + 5],
        fill=color
    )

    return img

# ================== ВСТАВКА ОБЕРНЕНОЇ СТРІЛКИ ==================
def paste_rotated_hand(base, hand_img, angle, offset_x):
    rotated = hand_img.rotate(
        angle,
        resample=Image.BICUBIC,
        expand=False
    )

    x = offset_x + C - rotated.width // 2
    y = C - rotated.height // 2

    base.alpha_composite(rotated, (x, y))

# ================== JSON ==================
def fetch_schedule():
    try:
        r = requests.get(JSON_URL, timeout=5)
        data = r.json()

        today = int(datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        ).timestamp())

        day = data["fact"]["data"].get(str(today), {}).get("GPV5.1", {}) # черга 5.1
        return {int(k): v for k, v in day.items()}

    except Exception as e:
        print("JSON error:", e)
        return {}

# ================== WIDGET ==================
class PowerClockWidget(tk.Tk):
    def __init__(self):
        super().__init__()

        TRANSPARENT = "red"

        self.overrideredirect(True)
        self.attributes("-transparentcolor", TRANSPARENT)

        self.geometry(f"{WIDTH}x{HEIGHT}+200+200")
        self.resizable(False, False)

        self.canvas = tk.Canvas(
            self,
            width=WIDTH,
            height=HEIGHT,
            bg=TRANSPARENT,
            highlightthickness=0
        )
        self.canvas.pack()

        self.bind("<Button-3>", lambda e: self.destroy())
        self.bind("<Button-1>", self.start_move)
        self.bind("<B1-Motion>", self.do_move)

        self._drag_x = self._drag_y = 0

        self.schedule = {}
        self._static_img = None

        # ⬇️ стрілки створюються ОДИН РАЗ
        self.minute_hand = create_hand(90, 4)
        self.hour_hand   = create_hand(70,  7)

        self.update_data()
        self.update_hands()

    # ---------- MOVE ----------
    def start_move(self, e):
        self._drag_x, self._drag_y = e.x, e.y

    def do_move(self, e):
        x = self.winfo_x() + e.x - self._drag_x
        y = self.winfo_y() + e.y - self._drag_y
        self.geometry(f"+{x}+{y}")

    # ---------- DATA ----------
    def update_data(self):
        self.schedule = fetch_schedule()

        am = draw_dial(range(1, 13), AM_TEMPLATE, self.schedule)
        pm = draw_dial(range(13, 25), PM_TEMPLATE, self.schedule)

        img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)

        d.ellipse(
            [BG_PADDING, BG_PADDING, SIZE - BG_PADDING, SIZE - BG_PADDING],
            fill=(255, 255, 255, 255)
        )
        d.ellipse(
            [
                SIZE + GAP + BG_PADDING,
                BG_PADDING,
                SIZE * 2 + GAP - BG_PADDING,
                SIZE - BG_PADDING
            ],
            fill=(255, 255, 255, 255)
        )

        img.paste(am, (0, 0), am)
        img.paste(pm, (SIZE + GAP, 0), pm)

        self._static_img = img
        self.after(UPDATE_DATA_MS, self.update_data)

    # ---------- HANDS ----------
    def update_hands(self):
        img = self._static_img.copy()
        now = datetime.now()

        minute_angle = 360 - now.minute * 6
        hour_angle   = 360 - (now.hour % 12) * 30 - now.minute * 0.5

        offset = 0 if now.hour < 12 else SIZE + GAP

        paste_rotated_hand(img, self.minute_hand, minute_angle, offset)
        paste_rotated_hand(img, self.hour_hand,   hour_angle, offset)

        self.tk_img = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)

        self.after(UPDATE_HANDS_MS, self.update_hands)

# ================== START ==================
if __name__ == "__main__":
    PowerClockWidget().mainloop()
