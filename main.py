import tkinter as tk
import random
import json
import os

root = tk.Tk()
root.attributes("-fullscreen", True)
root.update()

BASE_WIDTH = 1000
BASE_HEIGHT = 500
BASE_GROUND_Y = 420

current_w = root.winfo_screenwidth()
current_h = root.winfo_screenheight()

scale_x = current_w / BASE_WIDTH
scale_y = current_h / BASE_HEIGHT
scale_factor = min(scale_x, scale_y)

ground_y = int(BASE_GROUND_Y * scale_factor)

GRAVITY = 0.85 * scale_factor
JUMP_POWER = -13 * scale_factor
HOLD_BONUS = -0.7 * scale_factor
MAX_HOLD_FRAMES = 12

HS_FILE = "highscore.json"
root.configure(bg="#5c94fc")

canvas = tk.Canvas(root, width=current_w, height=current_h, bg="#5c94fc", highlightthickness=0)
canvas.pack(fill="both", expand=True)


# ---------------- JSON СИСТЕМА ----------------
def load_highscore():
    if os.path.exists(HS_FILE):
        try:
            with open(HS_FILE, "r") as f:
                return json.load(f).get("highscore", 0)
        except:
            return 0
    return 0


def save_highscore(new_high):
    try:
        with open(HS_FILE, "w") as f:
            json.dump({"highscore": new_high}, f)
    except:
        pass


# ---------------- STATE ИГРЫ ----------------
score = 0
highscore = load_highscore()
game_state = "menu"
speed = 8 * scale_factor
speed_timer = 0
spawn_timer = 40
coin_timer = 0
bg_offset = 0
velocity_y = 0
on_ground = True
is_space_held = False
jump_hold_counter = 0

pipes = []
coins = []

raw_sprites = {}
sprites = {}


# ---------------- ЗАГРУЗКА СПРАЙТОВ ----------------
def register_sprite(key, filename, base_zoom):
    try:
        img = Image.open(filename)
        raw_sprites[key] = (img, base_zoom, False)
    except:
        pass


def register_gif(key, filename, base_zoom):
    try:
        gif = Image.open(filename)
        frames = [f.convert("RGBA") for f in ImageSequence.Iterator(gif)]
        raw_sprites[key] = (frames, base_zoom, True)
    except:
        pass





def recompute_sprites():
    global sprites
    for key, (data, base_zoom, is_gif) in raw_sprites.items():
        final_zoom = max(1, round(base_zoom * scale_factor))
        if not is_gif:
            w, h = int(data.width * final_zoom), int(data.height * final_zoom)
            sprites[key] = ImageTk.PhotoImage(data.resize((w, h), Image.Resampling.NEAREST))
        else:
            frames_resized = []
            for frame in data:
                w, h = int(frame.width * final_zoom), int(frame.height * final_zoom)
                frames_resized.append(ImageTk.PhotoImage(frame.resize((w, h), Image.Resampling.NEAREST)))
            sprites[key] = frames_resized


recompute_sprites()


def get_mario_dims():
    img = sprites.get("mario_run1")
    return (img.width(), img.height()) if img else (int(40 * scale_factor), int(50 * scale_factor))


# ---------------- ИНИЦИАЛИЗАЦИЯ ГРАФИКИ ----------------
mario_x = int(120 * scale_factor)
mw, mh = get_mario_dims()
mario_y = ground_y - mh

# Бесконечная земля на весь экран
ground_rect1 = canvas.create_rectangle(0, ground_y, current_w + 500, current_h + 500, fill="#c84c0c", outline="")
ground_rect2 = canvas.create_rectangle(0, ground_y, current_w + 500, ground_y + max(5, int(12 * scale_factor)),
                                       fill="#fcb43c", outline="")

mario = canvas.create_image(mario_x, mario_y, anchor="nw", image=sprites.get("mario_run1"))

score_text = canvas.create_text(current_w - max(20, int(50 * scale_factor)), max(20, int(40 * scale_factor)), text="",
                                font=("Arial", max(14, int(20 * scale_factor)), "bold"), fill="white", anchor="ne")

# ЭЛЕМЕНТЫ НАЧАЛЬНОГО МЕНЮ
menu_title_text = canvas.create_text(
    current_w // 2, current_h // 2 - int(60 * scale_factor),
    text="SUPER MARIO RUNNER",
    font=("Arial", max(24, int(42 * scale_factor)), "bold"), fill="#fcb43c"
)
menu_start_text = canvas.create_text(
    current_w // 2, current_h // 2 + int(30 * scale_factor),
    text="PRESS SPACE TO START",
    font=("Arial", max(14, int(22 * scale_factor)), "bold"), fill="white"
)

game_over_text = None


# ---------------- ГЕНЕРАЦИЯ ОБЪЕКТОВ ----------------
def create_pipe():
    img = sprites.get("pipe")
    if not img: return
    w, h = img.width(), img.height()
    is_tall = random.choice([True, False])
    offset_y = 0 if is_tall else int(40 * scale_factor)
    pipe = canvas.create_image(current_w, ground_y - h + offset_y, anchor="nw", image=img)
    pipes.append({"id": pipe, "w": w, "h": h - offset_y})


def create_coin():
    frames = sprites.get("coin")
    if not frames: return
    y = random.randint(int(150 * scale_factor), int(280 * scale_factor))
    coin = canvas.create_image(current_w, y, anchor="nw", image=frames[0])
    coins.append({"id": coin, "frame": 0, "w": frames[0].width(), "h": frames[0].height()})


# ---------------- УПРАВЛЕНИЕ И ЛОГИКА ----------------
def start_game():
    global game_state, spawn_timer
    game_state = "playing"
    canvas.delete(menu_title_text)
    canvas.delete(menu_start_text)
    spawn_timer = 40
    update()


def jump_press(event):
    global velocity_y, on_ground, game_state, is_space_held, jump_hold_counter


    if game_state == "menu":
        start_game()
        return

    if game_state == "gameover":
        restart()
        return

    if game_state == "playing" and on_ground:
        velocity_y = JUMP_POWER
        on_ground = False
        is_space_held = True
        jump_hold_counter = 0
        if sprites.get("mario_jump"):
            canvas.itemconfig(mario, image=sprites.get("mario_jump"))


def jump_release(event):
    global is_space_held
    is_space_held = False


def game_over():
    global game_state, game_over_text, is_space_held, highscore
    game_state = "gameover"
    is_space_held = False
    if score > highscore:
        highscore = score
        save_highscore(highscore)

    game_over_text = canvas.create_text(
        current_w // 2, current_h // 2,
        text=f"GAME OVER\nScore: {score}\nBest: {highscore}\n\nPress SPACE or R to Restart",
        font=("Arial", max(16, int(26 * scale_factor)), "bold"), fill="white", justify="center"
    )


def restart(event=None):
    global score, game_state, mario_y, velocity_y, on_ground
    global spawn_timer, coin_timer, speed, speed_timer, is_space_held, game_over_text

    if game_state != "gameover": return

    for f in pipes + coins:
        canvas.delete(f["id"])

    pipes.clear()
    coins.clear()

    if game_over_text:
        canvas.delete(game_over_text)
        game_over_text = None

    score, spawn_timer, coin_timer, speed_timer = 0, 0, 0, 0
    speed = 8 * scale_factor
    velocity_y = 0
    on_ground = True
    is_space_held = False

    mario_y = ground_y - mh
    canvas.coords(mario, mario_x, mario_y)
    canvas.itemconfig(mario, image=sprites.get("mario_run1"))

    game_state = "playing"
    update()


# ---------------- ИГРОВОЙ ЦИКЛ ----------------
mario_anim_frame = 0


def update():
    global velocity_y, mario_y, on_ground, mario_anim_frame, is_space_held, jump_hold_counter, game_state
    global spawn_timer, coin_timer, speed_timer, speed, bg_offset, score, highscore, game_over_text

    if game_state != "playing":
        return

    bg_offset += 1
    speed_timer += 1

    if is_space_held and not on_ground:
        if jump_hold_counter < MAX_HOLD_FRAMES:
            velocity_y += HOLD_BONUS
            jump_hold_counter += 1
        else:
            is_space_held = False

    # Физика падения/прыжка
    velocity_y += GRAVITY
    mario_y += velocity_y
    if mario_y >= ground_y - mh:
        mario_y = ground_y - mh
        velocity_y = 0
        if not on_ground:
            on_ground = True

    canvas.coords(mario, mario_x, mario_y)

    # Анимация ног Марио
    if on_ground and bg_offset % 6 == 0:
        run_frames = [sprites.get("mario_run1"), sprites.get("mario_run2")]
        if run_frames[0]:
            mario_anim_frame = (mario_anim_frame + 1) % len(run_frames)
            canvas.itemconfig(mario, image=run_frames[mario_anim_frame])

    # Спавн препятствий
    spawn_timer += 1
    coin_timer += 1
    spawn_limit = max(45, 85 - int(((speed / scale_factor) - 8) * 4))

    if spawn_timer > spawn_limit:
        spawn_timer = 0
        create_pipe()

    if coin_timer > 110:
        coin_timer = 0
        create_coin()

    mx1, my1 = mario_x + int(6 * scale_factor), mario_y
    mx2, my2 = mx1 + mw - int(12 * scale_factor), mario_y + mh

    current_hi = max(score, highscore)
    canvas.itemconfig(score_text, text=f"Score: {score}   HI: {current_hi}")

    # Движение Труб
    for p in pipes[:]:
        pid = p["id"]
        canvas.move(pid, -speed, 0)
        px1, py1 = canvas.coords(pid)
        px2, py2 = px1 + p["w"], py1 + p["h"]
        if px2 < 0:
            canvas.delete(pid)
            pipes.remove(p)
            continue
        if mx2 > px1 and mx1 < px2 and my2 > py1 and my1 < py2:
            game_over()
            return

    # Движение Монеток
    coin_img_frames = sprites.get("coin")
    for c in coins[:]:
        cid = c["id"]
        canvas.move(cid, -speed, 0)
        cx1, cy1 = canvas.coords(cid)
        cx2, cy2 = cx1 + c["w"], cy1 + c["h"]
        if bg_offset % 5 == 0 and coin_img_frames:
            c["frame"] = (c["frame"] + 1) % len(coin_img_frames)
            canvas.itemconfig(cid, image=coin_img_frames[c["frame"]])
        if cx2 < 0:
            canvas.delete(cid)
            coins.remove(c)
            continue
        if mx2 > cx1 and mx1 < cx2 and my2 > cy1 and my1 < cy2:
            score += 25
            canvas.delete(cid)
            coins.remove(c)

    # Постепенное ускорение
    if speed_timer % 180 == 0:
        speed = min(speed + (0.8 * scale_factor), 22 * scale_factor)
        score += 30

    root.after(16, update)


# ---------------- ПРИВЯЗКА УПРАВЛЕНИЯ К ОКНУ ----------------
root.bind("<KeyPress-space>", jump_press)
root.bind("<KeyRelease-space>", jump_release)
root.bind("r", restart)
root.bind("R", restart)
root.bind("К", restart)
root.bind("к", restart)

# Кнопка закрытия игры
root.bind("<Escape>", lambda e: root.destroy())

root.mainloop()