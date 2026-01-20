# PowerClock24 v1.0

import tkinter as tk
from PIL import Image, ImageDraw, ImageTk, ImageFont
from math import sin, cos, radians
from datetime import datetime
import requests
import sys, os

# ================== НАЛАШТУВАННЯ ==================
SIZE = 400
WIDTH = SIZE
HEIGHT = SIZE

C = SIZE // 2

R_OUT = 148
R_IN  = 83

SECTORS = 24
STEP = 360 / SECTORS
HALF = STEP / 2

GREEN = (80, 180, 90, 190)
RED   = (220, 70, 70, 190)

BG_RADIUS = 160

MONTHS_UA = {
    1: "Січ",  2: "Лют",  3: "Бер",  4: "Кві",
    5: "Тра",  6: "Чер",  7: "Лип",  8: "Сер",
    9: "Вер", 10: "Жов", 11: "Лис", 12: "Гру"
}

FONT_SIZE = 18                   
CENTER_TEXT_OFFSET = 34           
CENTER_TEXT_COLOR = (0, 0, 0, 255)

BOX_PADDING_X = 6
BOX_PADDING_Y = 3
BOX_RADIUS = 1            # заокруглення
BOX_OUTLINE = (0, 0, 0, 180)
BOX_FILL = None           # або (255, 255, 255, 200)
BOX_WIDTH = 1

TITLE_TEXT = "Черга 5.1" # назва черги

TITLE_FONT_SIZE = 16
YEAR_FONT_SIZE  = 18

TITLE_OFFSET_Y = -45    # вище центру
YEAR_OFFSET_Y  = 55    # нижче центру

UPDATE_HANDS_MS = 60_000
UPDATE_DATA_MS  = 15 * 60_000

def resource_path(name):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, name)
    return os.path.join(os.path.abspath("."), name)

FONT_PATH = resource_path("JetBrainsMono-Regular.ttf") # шрифти 
TEMPLATE_24 = resource_path("powerClock-24-w.png") # шаблон

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

# ================== 24h ЦИФЕРБЛАТ ==================
def draw_dial_24(schedule):
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    for hour in range(24):
        state = schedule.get(hour + 1, "yes")

        start = -90 + hour * STEP
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

    template = Image.open(TEMPLATE_24).convert("RGBA")
    template = template.resize((SIZE, SIZE), Image.LANCZOS)

    return Image.alpha_composite(img, template)

# ================== ГОДИННА СТРІЛКА ==================
def create_hour_hand():
    length = 90
    width  = 4
    size = length * 2

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    cx = cy = size // 2

    d.rectangle(
        [cx - width // 2, cy - length, cx + width // 2, cy],
        fill=(0, 0, 0, 255)
    )

    d.ellipse(
        [cx - 6, cy - 6, cx + 6, cy + 6],
        fill=(0, 0, 0, 255)
    )

    return img

def paste_rotated_hand(base, hand_img, angle):
    rotated = hand_img.rotate(angle, Image.BICUBIC, expand=False)
    base.alpha_composite(
        rotated,
        (C - rotated.width // 2, C - rotated.height // 2)
    )

#================== місяць і день ===============
def draw_text_box_centered(
    d, text, cx, cy,
    font,
    text_color
):
    bbox = d.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    box_x0 = cx - text_w // 2 - BOX_PADDING_X
    box_x1 = cx + text_w // 2 + BOX_PADDING_X
    box_y0 = cy - text_h // 2 - BOX_PADDING_Y
    box_y1 = cy + text_h // 2 + BOX_PADDING_Y

    d.rounded_rectangle(
        [box_x0, box_y0, box_x1, box_y1],
        radius=BOX_RADIUS,
        outline=BOX_OUTLINE,
        width=BOX_WIDTH,
        fill=BOX_FILL
    )

    d.text(
        (cx, cy),
        text,
        fill=text_color,
        font=font,
        anchor="mm"
    )

def draw_center_text(img, now):
    d = ImageDraw.Draw(img)

    font_main = ImageFont.truetype(FONT_PATH, FONT_SIZE)
    font_title = ImageFont.truetype(FONT_PATH, TITLE_FONT_SIZE)
    font_year  = ImageFont.truetype(FONT_PATH, YEAR_FONT_SIZE)

    center_x = C
    center_y = C

    # ===== ЗВЕРХУ: "Черга 5.1"  =====
    d.text(
        (center_x, center_y + TITLE_OFFSET_Y),
        TITLE_TEXT,
        fill=CENTER_TEXT_COLOR,
        font=font_title,
        anchor="mm"
    )

    # ===== СЕРЕДИНА: місяць + день  =====
    y_mid = center_y + CENTER_TEXT_Y

    draw_text_box(
        d,
        MONTHS_UA[now.month],
        center_x - CENTER_TEXT_OFFSET,
        y_mid,
        font_main,
        anchor="rm",
        text_color=CENTER_TEXT_COLOR
    )

    draw_text_box(
        d,
        str(now.day),
        center_x + CENTER_TEXT_OFFSET,
        y_mid,
        font_main,
        anchor="lm",
        text_color=CENTER_TEXT_COLOR
    )

    # ===== ЗНИЗУ: рік =====
    draw_text_box_centered(
        d,
        str(now.year),
        center_x,
        center_y + YEAR_OFFSET_Y,
        font_year,
        text_color=CENTER_TEXT_COLOR
    )

#===============рамка тексту==============
def draw_text_box(
    d, text, center_x, center_y,
    font,
    anchor,
    text_color
):
    # розмір тексту
    bbox = d.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # координати тексту (з урахуванням anchor)
    if anchor == "rm":  # right-middle
        tx = center_x
        ty = center_y
        box_x0 = tx - text_w - BOX_PADDING_X
        box_x1 = tx + BOX_PADDING_X
    elif anchor == "lm":  # left-middle
        tx = center_x
        ty = center_y
        box_x0 = tx - BOX_PADDING_X
        box_x1 = tx + text_w + BOX_PADDING_X
    else:
        raise ValueError("Unsupported anchor")

    box_y0 = ty - text_h // 2 - BOX_PADDING_Y
    box_y1 = ty + text_h // 2 + BOX_PADDING_Y

    # рамка
    d.rounded_rectangle(
        [box_x0, box_y0, box_x1, box_y1],
        radius=BOX_RADIUS,
        outline=BOX_OUTLINE,
        width=BOX_WIDTH,
        fill=BOX_FILL
    )

    # текст
    d.text(
        (tx, ty),
        text,
        fill=text_color,
        font=font,
        anchor=anchor
    )

# ================== JSON ==================
def fetch_schedule():
    try:
        r = requests.get(JSON_URL, timeout=5)
        data = r.json()

        today = int(datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        ).timestamp())

        day = data["fact"]["data"].get(str(today), {}).get("GPV5.1", {})
        return {int(k): v for k, v in day.items()}

    except Exception as e:
        print("JSON error:", e)
        return {}

# ================== WIDGET ==================
class PowerClock24(tk.Tk):
    # ---------- POSITION ----------
    def save_position(self): # пам'ятає останнє положення на робочому столі
        x = self.winfo_x()
        y = self.winfo_y()
        with open("pos.txt", "w") as f:
            f.write(f"{x},{y}")

    def load_position(self):
        try:
            with open("pos.txt", "r") as f:
                x, y = f.read().split(",")
                self.geometry(f"+{x}+{y}")
        except:
            pass

    def on_close(self): # закриття по кліку ПКМ
        self.save_position()
        self.destroy()

    def __init__(self):
        super().__init__()

        TRANSPARENT = "gray"

        self.overrideredirect(True)
        self.attributes("-transparentcolor", TRANSPARENT)

        self.geometry(f"{WIDTH}x{HEIGHT}+200+200")
        self.resizable(False, False)

        self.load_position() 

        self.canvas = tk.Canvas(
            self,
            width=WIDTH,
            height=HEIGHT,
            bg=TRANSPARENT,
            highlightthickness=0
        )
        self.canvas.pack()

        self.bind("<Button-3>", lambda e: self.on_close())
        self.bind("<Button-1>", self.start_move) # перетягування зажатим ЛКМ
        self.bind("<B1-Motion>", self.do_move) 

        self._drag_x = self._drag_y = 0

        self.schedule = {}
        self._static_img = None

        self.hour_hand = create_hour_hand()

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

        dial = draw_dial_24(self.schedule)

        img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)

        d.ellipse(
            [
                C - BG_RADIUS,
                C - BG_RADIUS,
                C + BG_RADIUS,
                C + BG_RADIUS
            ],
            fill=(255, 255, 255, 255)
        )


        img.paste(dial, (0, 0), dial)

        self._static_img = img
        self.after(UPDATE_DATA_MS, self.update_data)

    # ---------- HAND ----------
    def update_hands(self):
        if not self._static_img:
            self.after(100, self.update_hands)
            return

        img = self._static_img.copy()
        now = datetime.now()

        hour_angle = 360 - now.hour * 15 - now.minute * 0.25

        paste_rotated_hand(img, self.hour_hand, hour_angle)

        draw_center_text(img, now)

        self.tk_img = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)

        self.after(UPDATE_HANDS_MS, self.update_hands)

# ================== START ==================
if __name__ == "__main__":
    PowerClock24().mainloop()
