import pygame
import random
import math
import sys

# ============================================================
# NEON WARZONE
# Polished 2D top-down FPS-style survival shooter
# No external assets required
# ============================================================

pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 1280, 720
FPS = 60
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("NEON WARZONE")
clock = pygame.time.Clock()

# Fonts
FONT = pygame.font.Font(None, 28)
SMALL = pygame.font.Font(None, 22)
MED = pygame.font.Font(None, 38)
BIG = pygame.font.Font(None, 72)
HUGE = pygame.font.Font(None, 110)

# Colors
BG = (5, 7, 15)
GRID = (16, 22, 38)
GRID2 = (24, 30, 50)
WHITE = (235, 245, 255)
CYAN = (40, 220, 255)
BLUE = (55, 120, 255)
RED = (255, 55, 75)
ORANGE = (255, 150, 45)
YELLOW = (255, 225, 70)
GREEN = (60, 235, 130)
PURPLE = (180, 80, 255)
DARK = (12, 15, 25)

WORLD_W, WORLD_H = 3000, 2200
PLAYER_SPEED = 300.0
BULLET_SPEED = 1150.0
MAX_AMMO = 30
FIRE_DELAY = 0.095

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)

def angle_to(ax, ay, bx, by):
    return math.atan2(by - ay, bx - ax)

def lerp(a, b, t):
    return a + (b - a) * t

def draw_text(text, font, color, pos, center=False, surface=screen):
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = pos
    else:
        rect.topleft = pos
    surface.blit(img, rect)
    return rect

def world_to_screen(x, y):
    return int(x - camera_x), int(y - camera_y)

# ------------------------------------------------------------
# Camera
# ------------------------------------------------------------

camera_x = 0.0
camera_y = 0.0
shake = 0.0

# ------------------------------------------------------------
# Particles
# ------------------------------------------------------------

particles = []

def spawn_particles(x, y, color, count=10, speed=220, life=0.45, size=4):
    for _ in range(count):
        a = random.random() * math.tau
        s = random.uniform(speed * 0.25, speed)
        particles.append({
            "x": x,
            "y": y,
            "vx": math.cos(a) * s,
            "vy": math.sin(a) * s,
            "life": random.uniform(life * 0.5, life),
            "max": life,
            "size": random.randint(max(2, size // 2), size),
            "color": color
        })

def update_particles(dt):
    for p in particles[:]:
        p["x"] += p["vx"] * dt
        p["y"] += p["vy"] * dt
        p["vx"] *= 0.94
        p["vy"] *= 0.94
        p["life"] -= dt
        if p["life"] <= 0:
            particles.remove(p)

def draw_particles():
    for p in particles:
        sx, sy = world_to_screen(p["x"], p["y"])
        if -20 < sx < WIDTH + 20 and -20 < sy < HEIGHT + 20:
            ratio = max(0, p["life"] / p["max"])
            r = max(1, int(p["size"] * ratio))
            pygame.draw.circle(screen, p["color"], (sx, sy), r)

# ------------------------------------------------------------
# Floating damage numbers
# ------------------------------------------------------------

floating = []

def add_damage_text(x, y, text, color=WHITE):
    floating.append({
        "x": x, "y": y, "text": str(text),
        "life": 0.75, "color": color
    })

def update_floating(dt):
    for f in floating[:]:
        f["y"] -= 45 * dt
        f["life"] -= dt
        if f["life"] <= 0:
            floating.remove(f)

def draw_floating():
    for f in floating:
        sx, sy = world_to_screen(f["x"], f["y"])
        draw_text(f["text"], SMALL, f["color"], (sx, sy), center=True)

# ------------------------------------------------------------
# Buildings / map
# ------------------------------------------------------------

buildings = []

def add_building(x, y, w, h, color):
    buildings.append({
        "rect": pygame.Rect(x, y, w, h),
        "color": color
    })

# Main city blocks
random.seed(7)
for gx in range(100, WORLD_W - 200, 300):
    for gy in range(100, WORLD_H - 200, 260):
        if random.random() < 0.82:
            w = random.randint(150, 230)
            h = random.randint(120, 190)
            add_building(
                gx + random.randint(-25, 25),
                gy + random.randint(-25, 25),
                w, h,
                random.choice([
                    (22, 29, 48),
                    (25, 32, 52),
                    (28, 30, 46),
                    (20, 35, 50)
                ])
            )

# Special central structures
add_building(1320, 760, 360, 240, (28, 34, 56))
add_building(720, 1260, 300, 220, (25, 34, 55))
add_building(2050, 1250, 330, 230, (30, 32, 55))

# Collision helpers

def circle_rect_collision(cx, cy, radius, rect):
    nx = clamp(cx, rect.left, rect.right)
    ny = clamp(cy, rect.top, rect.bottom)
    return (cx - nx) ** 2 + (cy - ny) ** 2 < radius ** 2

def blocked(x, y, radius):
    if x - radius < 0 or x + radius > WORLD_W:
        return True
    if y - radius < 0 or y + radius > WORLD_H:
        return True
    return any(circle_rect_collision(x, y, radius, b["rect"]) for b in buildings)

def move_entity(obj, dx, dy, radius):
    nx = obj["x"] + dx
    if not blocked(nx, obj["y"], radius):
        obj["x"] = nx
    ny = obj["y"] + dy
    if not blocked(obj["x"], ny, radius):
        obj["y"] = ny

# ------------------------------------------------------------
# Player
# ------------------------------------------------------------

player = {
    "x": WORLD_W / 2,
    "y": WORLD_H / 2,
    "radius": 22,
    "hp": 100,
    "max_hp": 100,
    "armor": 50,
    "max_armor": 50,
    "ammo": MAX_AMMO,
    "reserve": 150,
    "score": 0,
    "kills": 0,
    "level": 1,
    "xp": 0,
    "xp_next": 500,
    "stamina": 100,
    "max_stamina": 100,
    "reloading": False,
    "reload_timer": 0,
    "shoot_timer": 0,
    "invuln": 0,
    "muzzle": 0,
    "hit_flash": 0
}

# ------------------------------------------------------------
# Weapons
# ------------------------------------------------------------

weapons = [
    {
        "name": "VX-9 ASSAULT",
        "damage": 34,
        "delay": 0.095,
        "mag": 30,
        "reserve_max": 180,
        "spread": 0.035,
        "color": CYAN
    },
    {
        "name": "CR-12 HEAVY",
        "damage": 75,
        "delay": 0.48,
        "mag": 8,
        "reserve_max": 64,
        "spread": 0.012,
        "color": ORANGE
    },
    {
        "name": "PULSE SMG",
        "damage": 22,
        "delay": 0.055,
        "mag": 45,
        "reserve_max": 270,
        "spread": 0.07,
        "color": PURPLE
    }
]
weapon_index = 0

def current_weapon():
    return weapons[weapon_index]

# ------------------------------------------------------------
# Bullets
# ------------------------------------------------------------

bullets = []

def shoot(mouse_world_x, mouse_world_y):
    global shake

    if game_state != "playing" or player["reloading"]:
        return

    w = current_weapon()

    if player["shoot_timer"] > 0:
        return

    if player["ammo"] <= 0:
        reload_weapon()
        return

    player["ammo"] -= 1
    player["shoot_timer"] = w["delay"]
    player["muzzle"] = 0.08
    shake = min(14, shake + (5 if weapon_index != 1 else 9))

    a = angle_to(player["x"], player["y"], mouse_world_x, mouse_world_y)
    a += random.uniform(-w["spread"], w["spread"])

    bullets.append({
        "x": player["x"] + math.cos(a) * 28,
        "y": player["y"] + math.sin(a) * 28,
        "vx": math.cos(a) * BULLET_SPEED,
        "vy": math.sin(a) * BULLET_SPEED,
        "damage": w["damage"],
        "life": 1.2,
        "color": w["color"],
        "radius": 4 if weapon_index != 1 else 6
    })

    spawn_particles(
        player["x"] + math.cos(a) * 32,
        player["y"] + math.sin(a) * 32,
        YELLOW,
        5, 180, 0.18, 4
    )

def reload_weapon():
    if player["reloading"] or player["ammo"] >= current_weapon()["mag"]:
        return
    if player["reserve"] <= 0:
        return
    player["reloading"] = True
    player["reload_timer"] = 1.15 if weapon_index != 1 else 1.55

def finish_reload():
    w = current_weapon()
    need = w["mag"] - player["ammo"]
    take = min(need, player["reserve"])
    player["ammo"] += take
    player["reserve"] -= take
    player["reloading"] = False

# ------------------------------------------------------------
# Enemies
# ------------------------------------------------------------

enemies = []

def spawn_enemy():
    for _ in range(100):
        side = random.choice([0, 1, 2, 3])
        if side == 0:
            x, y = random.randint(50, WORLD_W - 50), 40
        elif side == 1:
            x, y = random.randint(50, WORLD_W - 50), WORLD_H - 40
        elif side == 2:
            x, y = 40, random.randint(50, WORLD_H - 50)
        else:
            x, y = WORLD_W - 40, random.randint(50, WORLD_H - 50)

        if dist(x, y, player["x"], player["y"]) > 650 and not blocked(x, y, 28):
            typ = random.random()
            if typ < 0.15:
                kind = "tank"
            elif typ < 0.35:
                kind = "runner"
            else:
                kind = "soldier"

            data = {
                "x": x, "y": y, "radius": 23,
                "kind": kind,
                "flash": 0,
                "attack": random.uniform(0.3, 1.4),
                "dead": False
            }

            if kind == "tank":
                data.update(hp=280, max_hp=280, speed=80, damage=18, reward=300, color=(230, 90, 45))
            elif kind == "runner":
                data.update(hp=80, max_hp=80, speed=230, damage=12, reward=150, color=(255, 70, 130))
            else:
                data.update(hp=120, max_hp=120, speed=125, damage=10, reward=100, color=RED)

            enemies.append(data)
            return

def kill_enemy(e):
    e["dead"] = True
    player["score"] += e["reward"]
    player["kills"] += 1
    player["xp"] += e["reward"]
    spawn_particles(e["x"], e["y"], e["color"], 30 if e["kind"] == "tank" else 18, 300, 0.7, 8)
    add_damage_text(e["x"], e["y"] - 35, f"+{e['reward']}", YELLOW)

    if random.random() < 0.08:
        pickups.append({
            "x": e["x"], "y": e["y"], "type": "armor", "life": 20
        })

def update_enemies(dt):
    global shake

    for e in enemies[:]:
        if e["dead"]:
            enemies.remove(e)
            continue

        e["flash"] = max(0, e["flash"] - dt)
        e["attack"] -= dt

        d = dist(e["x"], e["y"], player["x"], player["y"])

        if d < 950:
            a = angle_to(e["x"], e["y"], player["x"], player["y"])

            if d > player["radius"] + e["radius"] + 5:
                speed = e["speed"]
                move_entity(
                    e,
                    math.cos(a) * speed * dt,
                    math.sin(a) * speed * dt,
                    e["radius"]
                )

            if d < 58 and e["attack"] <= 0 and player["invuln"] <= 0:
                damage_player(e["damage"])
                e["attack"] = 0.85 if e["kind"] != "runner" else 0.55
                shake = min(18, shake + 8)

def damage_enemy(e, amount):
    if e["dead"]:
        return

    e["hp"] -= amount
    e["flash"] = 0.08
    add_damage_text(e["x"], e["y"] - 25, amount, YELLOW)
    spawn_particles(e["x"], e["y"], YELLOW, 5, 150, 0.25, 3)

    if e["hp"] <= 0:
        kill_enemy(e)

def damage_player(amount):
    if player["invuln"] > 0 or game_state != "playing":
        return

    player["invuln"] = 0.35
    player["hit_flash"] = 0.15

    armor_damage = min(player["armor"], amount * 0.65)
    player["armor"] -= armor_damage
    remaining = amount - armor_damage
    player["hp"] -= remaining

    spawn_particles(player["x"], player["y"], RED, 12, 220, 0.35, 5)

    if player["hp"] <= 0:
        player["hp"] = 0
        end_game()

# ------------------------------------------------------------
# Pickups
# ------------------------------------------------------------

pickups = []

def update_pickups(dt):
    for p in pickups[:]:
        p["life"] -= dt
        if p["life"] <= 0:
            pickups.remove(p)
            continue

        if dist(p["x"], p["y"], player["x"], player["y"]) < 45:
            if p["type"] == "armor":
                player["armor"] = min(player["max_armor"], player["armor"] + 25)
                add_damage_text(p["x"], p["y"], "+25 ARMOR", CYAN)
            pickups.remove(p)

# ------------------------------------------------------------
# Waves
# ------------------------------------------------------------

wave = 1
wave_timer = 0
wave_kills_target = 10
wave_kills = 0

def start_wave():
    global wave_timer, wave_kills, wave_kills_target
    wave_timer = 2.0
    wave_kills = 0
    wave_kills_target = 8 + wave * 4

def update_wave(dt):
    global wave, wave_timer, wave_kills

    if wave_timer > 0:
        wave_timer -= dt
        if wave_timer <= 0:
            for _ in range(min(5 + wave * 2, 22)):
                spawn_enemy()
        return

    if len(enemies) == 0 and wave_kills >= wave_kills_target:
        wave += 1
        player["reserve"] = min(
            current_weapon()["reserve_max"],
            player["reserve"] + 30
        )
        start_wave()

# ------------------------------------------------------------
# Leveling
# ------------------------------------------------------------

def update_level():
    while player["xp"] >= player["xp_next"]:
        player["xp"] -= player["xp_next"]
        player["level"] += 1
        player["xp_next"] = int(player["xp_next"] * 1.28)
        player["max_hp"] += 5
        player["hp"] = player["max_hp"]
        player["max_armor"] += 3
        player["armor"] = player["max_armor"]
        add_damage_text(player["x"], player["y"] - 60, "LEVEL UP!", GREEN)
        spawn_particles(player["x"], player["y"], GREEN, 35, 260, 0.9, 7)

# ------------------------------------------------------------
# Bullets update
# ------------------------------------------------------------

def update_bullets(dt):
    global shake

    for b in bullets[:]:
        b["x"] += b["vx"] * dt
        b["y"] += b["vy"] * dt
        b["life"] -= dt

        hit_wall = (
            b["x"] < 0 or b["x"] > WORLD_W or
            b["y"] < 0 or b["y"] > WORLD_H
        )

        if not hit_wall:
            for building in buildings:
                if building["rect"].collidepoint(int(b["x"]), int(b["y"])):
                    hit_wall = True
                    spawn_particles(b["x"], b["y"], ORANGE, 7, 180, 0.25, 3)
                    break

        if not hit_wall:
            for e in enemies:
                if not e["dead"] and dist(b["x"], b["y"], e["x"], e["y"]) < e["radius"] + b["radius"]:
                    damage_enemy(e, b["damage"])
                    shake = min(10, shake + 2)
                    hit_wall = True
                    break

        if hit_wall or b["life"] <= 0:
            if b in bullets:
                bullets.remove(b)

# ------------------------------------------------------------
# Drawing: map
# ------------------------------------------------------------

def draw_map():
    # Base
    screen.fill(BG)

    # Grid
    grid = 80
    start_x = int(camera_x // grid) * grid
    start_y = int(camera_y // grid) * grid

    for x in range(start_x, int(camera_x + WIDTH) + grid, grid):
        sx = x - int(camera_x)
        pygame.draw.line(screen, GRID, (sx, 0), (sx, HEIGHT))

    for y in range(start_y, int(camera_y + HEIGHT) + grid, grid):
        sy = y - int(camera_y)
        pygame.draw.line(screen, GRID, (0, sy), (WIDTH, sy))

    # Roads
    for x in range(0, WORLD_W, 300):
        sx = x - int(camera_x)
        pygame.draw.rect(screen, (9, 12, 22), (sx, 0, 70, HEIGHT))
        for yy in range(-50, HEIGHT + 100, 70):
            pygame.draw.rect(screen, (35, 38, 52), (sx + 33, yy, 4, 30))

    for y in range(0, WORLD_H, 260):
        sy = y - int(camera_y)
        pygame.draw.rect(screen, (9, 12, 22), (0, sy, WIDTH, 65))
        for xx in range(-50, WIDTH + 100, 70):
            pygame.draw.rect(screen, (35, 38, 52), (xx, sy + 30, 30, 4))

    # Buildings
    for b in buildings:
        r = b["rect"].move(-int(camera_x), -int(camera_y))
        if r.right < 0 or r.left > WIDTH or r.bottom < 0 or r.top > HEIGHT:
            continue

        # shadow
        shadow = r.move(9, 11)
        pygame.draw.rect(screen, (2, 3, 8), shadow, border_radius=5)

        pygame.draw.rect(screen, b["color"], r, border_radius=5)
        pygame.draw.rect(screen, (50, 62, 88), r, 2, border_radius=5)

        # windows
        for wx in range(r.left + 18, r.right - 10, 30):
            for wy in range(r.top + 18, r.bottom - 10, 32):
                if ((wx + wy) // 10) % 3 != 0:
                    pygame.draw.rect(
                        screen,
                        (35, 105, 150),
                        (wx, wy, 12, 8)
                    )

        # neon roof line
        pygame.draw.line(
            screen, (30, 100, 170),
            (r.left, r.top),
            (r.right, r.top), 2
        )

# ------------------------------------------------------------
# Drawing entities
# ------------------------------------------------------------

def draw_enemy(e):
    sx, sy = world_to_screen(e["x"], e["y"])
    r = e["radius"]

    if sx < -60 or sx > WIDTH + 60 or sy < -60 or sy > HEIGHT + 60:
        return

    # glow
    glow = pygame.Surface((r * 5, r * 5), pygame.SRCALPHA)
    pygame.draw.circle(
        glow,
        (*e["color"], 35),
        (r * 2.5, r * 2.5),
        r * 2.1
    )
    screen.blit(glow, (sx - r * 2.5, sy - r * 2.5))

    body_color = WHITE if e["flash"] > 0 else e["color"]

    pygame.draw.circle(screen, (4, 6, 12), (sx, sy), r + 5)
    pygame.draw.circle(screen, body_color, (sx, sy), r)

    # armor plates
    pygame.draw.circle(screen, (25, 30, 45), (sx, sy), r - 7, 3)

    # eyes
    pygame.draw.circle(screen, CYAN, (sx - 7, sy - 4), 3)
    pygame.draw.circle(screen, CYAN, (sx + 7, sy - 4), 3)

    # hp bar
    bw = 54 if e["kind"] != "tank" else 70
    bh = 6
    bx = sx - bw // 2
    by = sy - r - 16
    pygame.draw.rect(screen, (20, 20, 25), (bx, by, bw, bh))
    pygame.draw.rect(
        screen,
        RED,
        (bx, by, int(bw * max(0, e["hp"] / e["max_hp"])), bh)
    )

def draw_player(mouse_sx, mouse_sy):
    sx, sy = world_to_screen(player["x"], player["y"])
    r = player["radius"]

    # glow
    glow = pygame.Surface((130, 130), pygame.SRCALPHA)
    pygame.draw.circle(glow, (30, 180, 255, 28), (65, 65), 50)
    screen.blit(glow, (sx - 65, sy - 65))

    pygame.draw.circle(screen, (3, 8, 18), (sx, sy), r + 7)
    pygame.draw.circle(screen, BLUE, (sx, sy), r)
    pygame.draw.circle(screen, CYAN, (sx, sy), r - 6, 2)

    # gun
    a = angle_to(sx, sy, mouse_sx, mouse_sy)
    gx = sx + math.cos(a) * 34
    gy = sy + math.sin(a) * 34
    ex = sx + math.cos(a) * 64
    ey = sy + math.sin(a) * 64

    pygame.draw.line(screen, (8, 12, 20), (gx, gy), (ex, ey), 13)
    pygame.draw.line(screen, current_weapon()["color"], (gx, gy), (ex, ey), 7)

    if player["muzzle"] > 0:
        fx = sx + math.cos(a) * 76
        fy = sy + math.sin(a) * 76
        pygame.draw.circle(screen, YELLOW, (int(fx), int(fy)), 10)
        pygame.draw.circle(screen, WHITE, (int(fx), int(fy)), 4)

# ------------------------------------------------------------
# HUD
# ------------------------------------------------------------

def draw_bar(x, y, w, h, value, maximum, fg, bg=(20, 25, 35)):
    pygame.draw.rect(screen, bg, (x, y, w, h), border_radius=4)
    ratio = 0 if maximum <= 0 else clamp(value / maximum, 0, 1)
    pygame.draw.rect(screen, fg, (x, y, int(w * ratio), h), border_radius=4)
    pygame.draw.rect(screen, (100, 110, 130), (x, y, w, h), 1, border_radius=4)

def draw_hud():
    # top left
    panel = pygame.Surface((350, 128), pygame.SRCALPHA)
    panel.fill((5, 8, 16, 205))
    screen.blit(panel, (18, 18))

    draw_text("NEON WARZONE", MED, WHITE, (32, 28))
    draw_text(f"WAVE {wave}", FONT, CYAN, (32, 70))
    draw_text(f"KILLS {player['kills']}", FONT, WHITE, (150, 70))
    draw_text(f"SCORE {player['score']}", FONT, YELLOW, (32, 101))
    draw_text(f"LV {player['level']}", FONT, GREEN, (190, 101))

    # HP / armor
    draw_text("HP", SMALL, WHITE, (25, HEIGHT - 108))
    draw_bar(60, HEIGHT - 106, 250, 16, player["hp"], player["max_hp"], RED)

    draw_text("ARMOR", SMALL, WHITE, (25, HEIGHT - 80))
    draw_bar(75, HEIGHT - 78, 235, 12, player["armor"], player["max_armor"], CYAN)

    # XP
    draw_bar(
        25, HEIGHT - 48, 285, 8,
        player["xp"], player["xp_next"], GREEN
    )

    # weapon panel
    panel2 = pygame.Surface((310, 120), pygame.SRCALPHA)
    panel2.fill((5, 8, 16, 205))
    screen.blit(panel2, (WIDTH - 330, HEIGHT - 145))

    w = current_weapon()
    draw_text(w["name"], FONT, w["color"], (WIDTH - 310, HEIGHT - 130))
    draw_text(
        f"{player['ammo']:02d}",
        HUGE,
        WHITE,
        (WIDTH - 315, HEIGHT - 82)
    )
    draw_text(
        f"/ {player['reserve']:03d}",
        MED,
        (150, 170, 190),
        (WIDTH - 195, HEIGHT - 60)
    )

    if player["reloading"]:
        draw_text(
            "RELOADING...",
            MED,
            YELLOW,
            (WIDTH - 175, HEIGHT - 25),
            center=True
        )

    # wave announcement
    if wave_timer > 0:
        draw_text(
            f"WAVE {wave}",
            BIG,
            CYAN,
            (WIDTH // 2, 75),
            center=True
        )
        draw_text(
            "HOSTILES INCOMING",
            FONT,
            WHITE,
            (WIDTH // 2, 125),
            center=True
        )

# ------------------------------------------------------------
# Minimap
# ------------------------------------------------------------

def draw_minimap():
    size = 170
    x0 = WIDTH - size - 20
    y0 = 20

    mini = pygame.Surface((size, size), pygame.SRCALPHA)
    mini.fill((5, 8, 15, 210))

    # buildings
    for b in buildings:
        r = b["rect"]
        rx = int(r.x / WORLD_W * size)
        ry = int(r.y / WORLD_H * size)
        rw = max(2, int(r.w / WORLD_W * size))
        rh = max(2, int(r.h / WORLD_H * size))
        pygame.draw.rect(mini, (35, 48, 70), (rx, ry, rw, rh))

    # enemies
    for e in enemies:
        ex = int(e["x"] / WORLD_W * size)
        ey = int(e["y"] / WORLD_H * size)
        pygame.draw.circle(mini, RED, (ex, ey), 2)

    px = int(player["x"] / WORLD_W * size)
    py = int(player["y"] / WORLD_H * size)
    pygame.draw.circle(mini, CYAN, (px, py), 4)

    pygame.draw.rect(mini, (80, 120, 160), (0, 0, size - 1, size - 1), 2)
    screen.blit(mini, (x0, y0))

# ------------------------------------------------------------
# Menu / game state
# ------------------------------------------------------------

game_state = "menu"

def reset_game():
    global camera_x, camera_y, shake
    global bullets, particles, floating, pickups
    global enemies, wave, wave_timer, wave_kills, weapon_index

    player.update({
        "x": WORLD_W / 2,
        "y": WORLD_H / 2,
        "radius": 22,
        "hp": 100,
        "max_hp": 100,
        "armor": 50,
        "max_armor": 50,
        "ammo": current_weapon()["mag"],
        "reserve": current_weapon()["reserve_max"],
        "score": 0,
        "kills": 0,
        "level": 1,
        "xp": 0,
        "xp_next": 500,
        "stamina": 100,
        "max_stamina": 100,
        "reloading": False,
        "reload_timer": 0,
        "shoot_timer": 0,
        "invuln": 0,
        "muzzle": 0,
        "hit_flash": 0
    })

    bullets = []
    particles = []
    floating = []
    pickups = []
    enemies = []
    weapon_index = 0
    wave = 1
    wave_timer = 1.5
    wave_kills = 0

    for _ in range(7):
        spawn_enemy()

    camera_x = player["x"] - WIDTH / 2
    camera_y = player["y"] - HEIGHT / 2
    shake = 0

def end_game():
    global game_state
    game_state = "gameover"

# ------------------------------------------------------------
# Input / main
# ------------------------------------------------------------

pygame.mouse.set_visible(False)

reset_game()

running = True

while running:
    dt = min(clock.tick(FPS) / 1000.0, 0.033)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if game_state == "playing":
                    game_state = "paused"
                elif game_state == "paused":
                    game_state = "playing"

            if event.key == pygame.K_RETURN:
                if game_state in ("menu", "gameover"):
                    reset_game()
                    game_state = "playing"

            if event.key == pygame.K_r and game_state == "playing":
                reload_weapon()

            if event.key in (pygame.K_1, pygame.K_2, pygame.K_3) and game_state == "playing":
                new_index = event.key - pygame.K_1
                if new_index < len(weapons) and new_index != weapon_index:
                    weapon_index = new_index
                    player["ammo"] = min(player["ammo"], current_weapon()["mag"])
                    player["reserve"] = min(
                        player["reserve"],
                        current_weapon()["reserve_max"]
                    )

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1 and game_state == "menu":
                reset_game()
                game_state = "playing"

    if game_state == "playing":
        keys = pygame.key.get_pressed()
        mx, my = pygame.mouse.get_pos()

        # Mouse coordinates -> world
        mouse_world_x = mx + camera_x
        mouse_world_y = my + camera_y

        dx = int(keys[pygame.K_d]) - int(keys[pygame.K_a])
        dy = int(keys[pygame.K_s]) - int(keys[pygame.K_w])

        if dx or dy:
            length = math.hypot(dx, dy)
            dx /= length
            dy /= length

            move_entity(
                player,
                dx * PLAYER_SPEED * dt,
                dy * PLAYER_SPEED * dt,
                player["radius"]
            )

        if pygame.mouse.get_pressed()[0]:
            shoot(mouse_world_x, mouse_world_y)

        # Timers
        player["shoot_timer"] = max(0, player["shoot_timer"] - dt)
        player["muzzle"] = max(0, player["muzzle"] - dt)
        player["invuln"] = max(0, player["invuln"] - dt)
        player["hit_flash"] = max(0, player["hit_flash"] - dt)

        if player["reloading"]:
            player["reload_timer"] -= dt
            if player["reload_timer"] <= 0:
                finish_reload()

        # Camera follows player smoothly
        target_x = player["x"] - WIDTH / 2
        target_y = player["y"] - HEIGHT / 2
        camera_x = lerp(camera_x, target_x, min(1, dt * 8))
        camera_y = lerp(camera_y, target_y, min(1, dt * 8))
        camera_x = clamp(camera_x, 0, WORLD_W - WIDTH)
        camera_y = clamp(camera_y, 0, WORLD_H - HEIGHT)

        update_bullets(dt)
        update_enemies(dt)
        update_particles(dt)
        update_floating(dt)
        update_pickups(dt)
        update_wave(dt)
        update_level()

    elif game_state in ("menu", "gameover", "paused"):
        update_particles(dt)
        update_floating(dt)

    # Camera shake
    sx_shake = random.uniform(-shake, shake) if shake > 0 else 0
    sy_shake = random.uniform(-shake, shake) if shake > 0 else 0
    old_cx, old_cy = camera_x, camera_y
    camera_x += sx_shake
    camera_y += sy_shake
    shake = max(0, shake - 30 * dt)

    # Draw
    draw_map()

    # Pickups
    for p in pickups:
        sx, sy = world_to_screen(p["x"], p["y"])
        pygame.draw.circle(screen, CYAN, (sx, sy), 12, 2)
        pygame.draw.rect(screen, CYAN, (sx - 5, sy - 5, 10, 10), 2)

    for b in bullets:
        sx, sy = world_to_screen(b["x"], b["y"])
        pygame.draw.circle(screen, b["color"], (sx, sy), b["radius"])
        pygame.draw.circle(screen, WHITE, (sx, sy), max(1, b["radius"] // 2))

    for e in enemies:
        draw_enemy(e)

    mx, my = pygame.mouse.get_pos()
    draw_player(mx, my)

    draw_particles()
    draw_floating()

    camera_x, camera_y = old_cx, old_cy

    if game_state == "playing":
        draw_hud()
        draw_minimap()

        # Crosshair
        pygame.draw.circle(screen, WHITE, (mx, my), 11, 1)
        pygame.draw.line(screen, WHITE, (mx - 18, my), (mx - 6, my), 2)
        pygame.draw.line(screen, WHITE, (mx + 6, my), (mx + 18, my), 2)
        pygame.draw.line(screen, WHITE, (mx, my - 18), (mx, my - 6), 2)
        pygame.draw.line(screen, WHITE, (mx, my + 6), (mx, my + 18), 2)

        # Hit / damage vignette
        if player["hit_flash"] > 0:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 20, 30, 70))
            screen.blit(overlay, (0, 0))

    elif game_state == "menu":
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((2, 4, 12, 180))
        screen.blit(overlay, (0, 0))

        draw_text("NEON", HUGE, CYAN, (WIDTH // 2, 190), center=True)
        draw_text("WARZONE", HUGE, WHITE, (WIDTH // 2, 290), center=True)
        draw_text(
            "TACTICAL SURVIVAL // SECTOR 07",
            FONT, (120, 150, 180),
            (WIDTH // 2, 360), center=True
        )

        draw_text(
            "ENTER / LEFT CLICK  :  START",
            MED, WHITE,
            (WIDTH // 2, 455), center=True
        )
        draw_text(
            "WASD  MOVE     LMB  FIRE     R  RELOAD     1-3  WEAPONS     ESC  PAUSE",
            SMALL, (150, 180, 205),
            (WIDTH // 2, 510), center=True
        )

        draw_text(
            "PYTHON + PYGAME",
            SMALL, (70, 100, 125),
            (WIDTH // 2, 650), center=True
        )

    elif game_state == "paused":
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        draw_text("PAUSED", BIG, WHITE, (WIDTH // 2, 280), center=True)
        draw_text("PRESS ESC TO RESUME", MED, CYAN, (WIDTH // 2, 360), center=True)

    elif game_state == "gameover":
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((8, 0, 8, 185))
        screen.blit(overlay, (0, 0))

        draw_text("MISSION FAILED", BIG, RED, (WIDTH // 2, 235), center=True)
        draw_text(
            f"SCORE {player['score']}   //   KILLS {player['kills']}   //   WAVE {wave}",
            MED, WHITE,
            (WIDTH // 2, 320), center=True
        )
        draw_text(
            "PRESS ENTER TO REDEPLOY",
            MED, CYAN,
            (WIDTH // 2, 430), center=True
        )

    pygame.display.flip()

pygame.quit()
sys.exit()
