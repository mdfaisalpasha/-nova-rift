import pygame
import math
import random
import sys
import json
import os

# Initialize Pygame
pygame.init()

# Constants & Setup
# Fetch the desktop's native width and height
infoObject = pygame.display.Info()
WIDTH, HEIGHT = infoObject.current_w, infoObject.current_h

FPS = 60
WHITE = (255, 255, 255)
BLACK = (0, 0, 5)
P1_COLOR = (0, 245, 255)
COCKPIT_COLOR = (200, 255, 255)
HP_COLOR = (50, 255, 50)
WEAPON_COLOR = (0, 150, 255)
SHIELD_COLOR = (180, 50, 255) 
SCORE_FILE = "nova_scores.json"

# Apply dynamic resolution and FULLSCREEN flag
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("NOVA RIFT - Ultimate Arcade Edition")
clock = pygame.time.Clock()

# --- GLOBAL VFX STATE ---
screen_shake = 0

def apply_shake():
    global screen_shake
    if screen_shake > 0:
        screen_shake *= 0.9
        if screen_shake < 0.5: screen_shake = 0
        return random.randint(-int(screen_shake), int(screen_shake)), random.randint(-int(screen_shake), int(screen_shake))
    return 0, 0

def add_shake(amount):
    global screen_shake
    screen_shake = min(screen_shake + amount, 30)

# --- HIGH SCORE SYSTEM ---
def load_scores():
    if os.path.exists(SCORE_FILE):
        try:
            with open(SCORE_FILE, "r") as f: return json.load(f)
        except: return []
    return []

def save_score(name, score):
    if score <= 0: return 
    scores = load_scores()
    scores.append({"name": name, "score": score})
    scores = sorted(scores, key=lambda x: x["score"], reverse=True)
    with open(SCORE_FILE, "w") as f: json.dump(scores, f)

def rotate_point(x, y, angle):
    return x * math.cos(angle) - y * math.sin(angle), x * math.sin(angle) + y * math.cos(angle)

# --- VFX CLASSES ---
class Particle:
    def __init__(self, x, y, vx, vy, life, color, size=2, glow=False):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size
        self.glow = glow

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.94
        self.vy *= 0.94
        self.life -= 1

    def draw(self, surface, offset_x, offset_y):
        if self.life > 0:
            alpha = max(0, min(255, int(255 * (self.life / self.max_life))))
            draw_x, draw_y = int(self.x + offset_x), int(self.y + offset_y)
            
            if self.glow:
                s = pygame.Surface((self.size*4, self.size*4), pygame.SRCALPHA)
                pygame.draw.circle(s, (*self.color[:3], alpha // 3), (self.size*2, self.size*2), self.size*2)
                pygame.draw.circle(s, (*self.color[:3], alpha), (self.size*2, self.size*2), self.size)
                surface.blit(s, (draw_x - self.size*2, draw_y - self.size*2), special_flags=pygame.BLEND_RGBA_ADD)
            else:
                s = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
                pygame.draw.circle(s, (*self.color[:3], alpha), (self.size, self.size), self.size)
                surface.blit(s, (draw_x - self.size, draw_y - self.size))

class Shockwave:
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        self.radius = 1
        self.life = 20
        self.max_life = 20
        self.color = color

    def update(self):
        self.radius += 8
        self.life -= 1

    def draw(self, surface, offset_x, offset_y):
        if self.life > 0:
            alpha = max(0, min(255, int(255 * (self.life / self.max_life))))
            s = pygame.Surface((self.radius*2, self.radius*2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*self.color[:3], alpha), (self.radius, self.radius), self.radius, 3)
            surface.blit(s, (int(self.x + offset_x - self.radius), int(self.y + offset_y - self.radius)))

class FloatingText:
    def __init__(self, x, y, text, color):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.life = 40
        self.max_life = 40
        self.vy = -1.5

    def update(self):
        self.y += self.vy
        self.life -= 1

    def draw(self, surface, font, offset_x, offset_y):
        if self.life > 0:
            alpha = max(0, min(255, int(255 * (self.life / self.max_life))))
            txt_surf = font.render(self.text, True, self.color)
            txt_surf.set_alpha(alpha)
            surface.blit(txt_surf, (self.x + offset_x - txt_surf.get_width()//2, self.y + offset_y))

# --- GAME ENTITIES ---
class Bullet:
    def __init__(self, x, y, angle, speed, color, damage, is_enemy=False):
        self.x, self.y = x, y
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.color = color
        self.damage = damage
        self.is_enemy = is_enemy
        self.life = 100

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, surface, offset_x, offset_y):
        pygame.draw.line(surface, self.color, 
                         (self.x - self.vx*0.5 + offset_x, self.y - self.vy*0.5 + offset_y), 
                         (self.x + offset_x, self.y + offset_y), 4)

class PowerUp:
    def __init__(self, x, y, p_type):
        self.x, self.y = x, y
        self.type = p_type  # "HP", "WEAPON", or "SHIELD"
        self.vy = 1.5
        self.pulse_timer = 0
        self.dead = False
        
        if p_type == "HP": self.color = HP_COLOR
        elif p_type == "WEAPON": self.color = WEAPON_COLOR
        else: self.color = SHIELD_COLOR

    def update(self):
        self.y += self.vy
        self.pulse_timer += 0.15
        if self.y > HEIGHT + 50: self.dead = True

    def draw(self, surface, offset_x, offset_y):
        pulse = math.sin(self.pulse_timer) * 4
        dx, dy = int(self.x + offset_x), int(self.y + offset_y)
        
        pygame.draw.circle(surface, self.color, (dx, dy), int(16 + pulse), 2)
        
        if self.type == "HP":
            pygame.draw.line(surface, self.color, (dx - 8, dy), (dx + 8, dy), 3)
            pygame.draw.line(surface, self.color, (dx, dy - 8), (dx, dy + 8), 3)
        elif self.type == "WEAPON":
            pygame.draw.line(surface, self.color, (dx - 6, dy + 2), (dx, dy - 6), 3)
            pygame.draw.line(surface, self.color, (dx, dy - 6), (dx + 6, dy + 2), 3)
            pygame.draw.line(surface, self.color, (dx - 6, dy + 8), (dx, dy), 3)
            pygame.draw.line(surface, self.color, (dx, dy), (dx + 6, dy + 8), 3)
        elif self.type == "SHIELD":
            pts = [(dx, dy - 8), (dx + 8, dy), (dx, dy + 8), (dx - 8, dy)]
            pygame.draw.polygon(surface, self.color, pts, 3)

class Ship:
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        self.vx, self.vy = 0, 0
        self.color = color
        self.angle = -math.pi / 2
        self.hp = 100
        self.max_hp = 100
        self.shoot_cd = 0
        self.dead = False
        self.score = 0
        
        self.dash_energy = 0
        self.dash_timer = 0
        self.is_dashing = False
        self.weapon_boost_timer = 0
        self.shield_timer = 0

    def update(self, keys, mouse_pos, mouse_clicked, right_clicked):
        if self.dead: return
        spd = 0.5 if not self.is_dashing else 2.0
        fric = 0.85 if not self.is_dashing else 0.98
        max_v = 8.0 if not self.is_dashing else 22.0

        if keys[pygame.K_a] or keys[pygame.K_LEFT]: self.vx -= spd
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: self.vx += spd
        if keys[pygame.K_w] or keys[pygame.K_UP]: self.vy -= spd
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: self.vy += spd
        
        mx, my = mouse_pos
        if not self.is_dashing:
            if math.hypot(mx - self.x, my - self.y) > 10:
                self.vx += (mx - self.x) * 0.03
                self.vy += (my - self.y) * 0.03

        if (keys[pygame.K_LSHIFT] or right_clicked) and self.dash_energy >= 100 and not self.is_dashing:
            self.is_dashing = True
            self.dash_timer = 18 
            self.dash_energy = 0
            add_shake(5)
            spawn_explosion(self.x, self.y, self.color, count=10, speed=4)

        if self.is_dashing:
            self.dash_timer -= 1
            if self.dash_timer % 3 == 0: self.shoot(is_dash_burst=True)
            if self.dash_timer <= 0: self.is_dashing = False
        
        if self.weapon_boost_timer > 0: self.weapon_boost_timer -= 1
        if self.shield_timer > 0: self.shield_timer -= 1

        if (keys[pygame.K_SPACE] or mouse_clicked) and self.shoot_cd <= 0 and not self.is_dashing: 
            self.shoot()

        self.vx = max(-max_v, min(max_v, self.vx))
        self.vy = max(-max_v, min(max_v, self.vy))
        self.x += self.vx
        self.y += self.vy
        self.vx *= fric
        self.vy *= fric
        
        self.x = max(20, min(WIDTH - 50, self.x))
        self.y = max(20, min(HEIGHT - 20, self.y))
        if self.shoot_cd > 0: self.shoot_cd -= 1

        if self.hp <= self.max_hp * 0.4:
            particles.append(Particle(self.x + random.uniform(-8, 8), self.y + 10, 
                                      random.uniform(-1.5, 1.5), random.uniform(2, 4), 
                                      life=45, color=(60, 60, 60), size=random.randint(6, 12)))
            if random.random() < 0.6:
                particles.append(Particle(self.x + random.uniform(-10, 10), self.y, 
                                          random.uniform(-2, 2), random.uniform(1, 4), 
                                          life=25, color=(255, 100, 0), size=random.randint(3, 6), glow=True))

    def shoot(self, is_dash_burst=False):
        global level
        
        if self.weapon_boost_timer > 0:
            self.shoot_cd = 5
        else:
            self.shoot_cd = max(6, 14 - level) 
            
        base_y = self.y - 25
        
        if is_dash_burst:
            bullets.append(Bullet(self.x, base_y, self.angle, 25, WHITE, 20, False))
            bullets.append(Bullet(self.x - 15, base_y + 10, self.angle - 0.15, 25, self.color, 20, False))
            bullets.append(Bullet(self.x + 15, base_y + 10, self.angle + 0.15, 25, self.color, 20, False))
            bullets.append(Bullet(self.x - 30, base_y + 20, self.angle - 0.3, 25, self.color, 20, False))
            bullets.append(Bullet(self.x + 30, base_y + 20, self.angle + 0.3, 25, self.color, 20, False))
            return

        active_level = level
        if self.weapon_boost_timer > 0:
            active_level += 1 

        if active_level == 1:
            bullets.append(Bullet(self.x, base_y, self.angle, 18, self.color, 10, False))
        elif active_level == 2:
            bullets.append(Bullet(self.x - 10, base_y, self.angle, 18, self.color, 10, False))
            bullets.append(Bullet(self.x + 10, base_y, self.angle, 18, self.color, 10, False))
        elif active_level == 3:
            bullets.append(Bullet(self.x, base_y - 5, self.angle, 18, self.color, 10, False))
            bullets.append(Bullet(self.x - 12, base_y, self.angle - 0.15, 18, self.color, 10, False))
            bullets.append(Bullet(self.x + 12, base_y, self.angle + 0.15, 18, self.color, 10, False))
        else: 
            bullets.append(Bullet(self.x - 15, base_y, self.angle - 0.2, 18, self.color, 10, False))
            bullets.append(Bullet(self.x - 5, base_y - 5, self.angle - 0.05, 18, self.color, 10, False))
            bullets.append(Bullet(self.x + 5, base_y - 5, self.angle + 0.05, 18, self.color, 10, False))
            bullets.append(Bullet(self.x + 15, base_y, self.angle + 0.2, 18, self.color, 10, False))

    def draw(self, surface, offset_x, offset_y):
        if self.dead: return
        
        if self.shield_timer > 0:
            pulse = math.sin(pygame.time.get_ticks() * 0.015) * 4
            s_rad = int(45 + pulse)
            pygame.draw.circle(surface, SHIELD_COLOR, (int(self.x + offset_x), int(self.y + offset_y)), s_rad, 3)
            s_surf = pygame.Surface((s_rad*2, s_rad*2), pygame.SRCALPHA)
            pygame.draw.circle(s_surf, (*SHIELD_COLOR[:3], 40), (s_rad, s_rad), s_rad)
            surface.blit(s_surf, (int(self.x + offset_x - s_rad), int(self.y + offset_y - s_rad)))

        if self.weapon_boost_timer > 0:
            pulse = math.sin(pygame.time.get_ticks() * 0.01) * 5
            pygame.draw.circle(surface, WEAPON_COLOR, (int(self.x + offset_x), int(self.y + offset_y)), int(35 + pulse), 2)
            
        if self.is_dashing:
            pygame.draw.circle(surface, self.color, (int(self.x + offset_x), int(self.y + offset_y)), 30, 2)

        fuselage_pts = [(0, -25), (-6, -10), (-5, 15), (-2, 20), (2, 20), (5, 15), (6, -10)]
        main_wings = [(-5, -5), (-35, 5), (-35, 12), (-5, 8), (5, 8), (35, 12), (35, 5), (5, -5)]
        tail_wings = [(-3, 12), (-15, 18), (-15, 22), (-2, 20), (2, 20), (15, 22), (15, 18), (3, 12)]
        cockpit_pts = [(0, -12), (-4, -5), (0, 2), (4, -5)]
        engine_pts = [(-4, 20), (-6, 30), (0, 25), (6, 30), (4, 20)]

        def transform(pts):
            return [(self.x + rotate_point(px, py, self.angle + math.pi/2)[0] + offset_x, 
                     self.y + rotate_point(px, py, self.angle + math.pi/2)[1] + offset_y) for px, py in pts]

        flame_len = random.randint(2, 6) if not self.is_dashing else 20
        flame = transform([(px, py + flame_len) for px, py in engine_pts])
        pygame.draw.polygon(surface, (0, 200, 255) if self.is_dashing else (0, 150, 255), flame)
        
        alpha = 255 if not self.is_dashing else 120 
        body_color = (*self.color[:3], alpha)
        
        s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(s, (40, 40, 40, alpha), transform(tail_wings))
        pygame.draw.polygon(s, body_color, transform(tail_wings), 2)
        pygame.draw.polygon(s, (50, 50, 50, alpha), transform(main_wings))
        pygame.draw.polygon(s, body_color, transform(main_wings), 2)
        pygame.draw.polygon(s, (60, 60, 60, alpha), transform(fuselage_pts))
        pygame.draw.polygon(s, body_color, transform(fuselage_pts), 2)
        pygame.draw.polygon(s, (*COCKPIT_COLOR[:3], alpha), transform(cockpit_pts))
        surface.blit(s, (0,0))

class Enemy:
    def __init__(self, x, y, level):
        self.x, self.y = x, y
        self.dead = False
        self.timer = random.randint(0, 100)
        self.angle = math.pi / 2 
        
        rand = random.random()
        if rand < 0.2 and level > 1:
            self.type = "SCOUT"
            self.hp = 15 + (level * 2)
            self.speed = 3.5 + (level * 0.3)
            self.color = (200, 50, 255)
            self.shoot_cd = 9999 
        elif rand > 0.8 and level > 2:
            self.type = "CRUISER"
            self.hp = 60 + (level * 5)
            self.speed = 0.8 + (level * 0.1)
            self.color = (255, 200, 0)
            self.shoot_cd = 80
        else:
            self.type = "FIGHTER"
            self.hp = 30 + (level * 3)
            self.speed = 1.5 + (level * 0.2)
            self.color = (255, 60, 60)
            self.shoot_cd = random.randint(60, 100)

    def update(self):
        self.timer += 1
        self.y += self.speed
        
        if self.type == "SCOUT":
            if player.x < self.x: self.x -= 1.5
            elif player.x > self.x: self.x += 1.5
        elif self.type == "FIGHTER":
            self.x += math.sin(self.timer * 0.05) * 2
        elif self.type == "CRUISER":
            self.x += math.sin(self.timer * 0.02) * 1

        self.shoot_cd -= 1
        if self.shoot_cd <= 0:
            if self.type == "FIGHTER":
                bullets.append(Bullet(self.x, self.y + 15, self.angle, 8, (255, 100, 0), 10, True))
                self.shoot_cd = max(40, 100 - level*5)
            elif self.type == "CRUISER":
                bullets.append(Bullet(self.x, self.y + 20, self.angle - 0.2, 6, (255, 50, 0), 15, True))
                bullets.append(Bullet(self.x, self.y + 20, self.angle + 0.2, 6, (255, 50, 0), 15, True))
                self.shoot_cd = max(60, 120 - level*5)

        if self.y > HEIGHT + 50: self.dead = True

    def draw(self, surface, offset_x, offset_y):
        if self.dead: return
        def transform(pts): return [(self.x + px + offset_x, self.y + py + offset_y) for px, py in pts]
        
        if self.type == "SCOUT":
            hull = [(0, 15), (-10, -15), (0, -5), (10, -15)]
        elif self.type == "CRUISER":
            hull = [(0, 25), (-25, -5), (-15, -20), (15, -20), (25, -5)]
        else:
            hull = [(0, 20), (-15, -10), (-8, -5), (8, -5), (15, -10)]
            
        pygame.draw.polygon(surface, (40, 10, 10), transform(hull))
        pygame.draw.polygon(surface, self.color, transform(hull), 2)
        pygame.draw.circle(surface, (255, 255, 255), (int(self.x + offset_x), int(self.y + 5 + offset_y)), 3)

# --- SYSTEM SETUP ---
player = Ship(WIDTH // 2, HEIGHT * 0.8, P1_COLOR)
bullets, enemies, particles, shockwaves, floating_texts, powerups = [], [], [], [], [], []
stars = [(random.randint(0, WIDTH), random.randint(0, HEIGHT), random.uniform(0.2, 2.0), random.uniform(0.5, 2.0)) for _ in range(200)]

wave_timer = 0
level = 1
enemies_destroyed = 0
level_display_timer = 0
user_name = ""
game_state = "MENU" 
leaderboard_scroll = 0 

# Fonts
score_font = pygame.font.SysFont("Courier New", 24, bold=True)
mini_font = pygame.font.SysFont("Courier New", 16, bold=True)
title_font = pygame.font.SysFont("Courier New", 70, bold=True)
menu_font = pygame.font.SysFont("Courier New", 30, bold=True)

# Rectangles (these will dynamically center based on screen size now)
btn_play = pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 - 20, 300, 60)
btn_scores = pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 + 60, 300, 60)
btn_quit = pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 + 140, 300, 60)

# Game Over Menu Rectangles
btn_same_pilot = pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 - 20, 300, 60)
btn_new_pilot = pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 + 60, 300, 60)
btn_go_menu = pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 + 140, 300, 60)

# Leaderboard Back Button
btn_back_scores = pygame.Rect(WIDTH // 2 - 150, HEIGHT - 100, 300, 60)

# In-Game Abort Button (Top Right)
btn_in_game_menu = pygame.Rect(WIDTH - 150, 20, 130, 40)

def spawn_explosion(x, y, color, count=25, speed=8, shock=True):
    if shock: shockwaves.append(Shockwave(x, y, color))
    for _ in range(count):
        angle = random.uniform(0, math.pi * 2)
        spd = random.uniform(1, speed)
        particles.append(Particle(x, y, math.cos(angle)*spd, math.sin(angle)*spd, random.randint(20, 50), color, glow=True))

def reset_game():
    global wave_timer, level, enemies_destroyed, level_display_timer
    player.hp = 100
    player.score = 0
    player.dead = False
    player.x, player.y = WIDTH // 2, HEIGHT * 0.8
    player.vx, player.vy = 0, 0
    player.is_dashing = False
    player.dash_energy = 0
    player.weapon_boost_timer = 0
    player.shield_timer = 0
    bullets.clear()
    enemies.clear()
    particles.clear()
    shockwaves.clear()
    floating_texts.clear()
    powerups.clear()
    wave_timer = 0
    level = 1
    enemies_destroyed = 0
    level_display_timer = 120

# --- MAIN LOOP ---
running = True
while running:
    keys = pygame.key.get_pressed()
    mouse_pos = pygame.mouse.get_pos()
    mouse_clicked = False
    right_clicked = False
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        
        # Emergency exit key for fullscreen mode
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE and game_state != "NAME_INPUT":
                running = False
                
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: mouse_clicked = True
            if event.button == 3: right_clicked = True
            
        if game_state == "MENU":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_play.collidepoint(event.pos):
                    user_name = "" 
                    game_state = "NAME_INPUT"
                elif btn_scores.collidepoint(event.pos): 
                    leaderboard_scroll = 0
                    game_state = "HIGH_SCORES"
                elif btn_quit.collidepoint(event.pos): running = False
        
        elif game_state == "NAME_INPUT":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if user_name.strip() == "": user_name = "Unknown Pilot"
                    reset_game()
                    game_state = "PLAYING"
                elif event.key == pygame.K_BACKSPACE: user_name = user_name[:-1]
                elif event.key == pygame.K_ESCAPE: game_state = "MENU"
                else:
                    if len(user_name) < 15 and event.unicode.isprintable(): user_name += event.unicode
        
        elif game_state == "HIGH_SCORES":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and btn_back_scores.collidepoint(event.pos):
                game_state = "MENU"
            if event.type == pygame.MOUSEWHEEL:
                leaderboard_scroll += event.y * 40
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP: leaderboard_scroll += 40
                if event.key == pygame.K_DOWN: leaderboard_scroll -= 40

        elif game_state == "PLAYING":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Check for in-game abort button
                if btn_in_game_menu.collidepoint(event.pos):
                    save_score(user_name, player.score)
                    game_state = "MENU"

        elif game_state == "GAME_OVER":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_same_pilot.collidepoint(event.pos):
                    reset_game()
                    game_state = "PLAYING"
                elif btn_new_pilot.collidepoint(event.pos):
                    user_name = "" 
                    game_state = "NAME_INPUT" 
                elif btn_go_menu.collidepoint(event.pos):
                    game_state = "MENU"

    if game_state == "PLAYING" or game_state == "GAME_OVER":
        # Continuously poll mouse for shooting/moving
        mouse_clicked = pygame.mouse.get_pressed()[0]
        right_clicked = pygame.mouse.get_pressed()[2]

    screen.fill(BLACK)
    off_x, off_y = apply_shake()
    
    speed_mult = 3 if player.is_dashing else 1
    for i, (sx, sy, size, spd) in enumerate(stars):
        sy += spd * speed_mult
        if sy > HEIGHT: sy = 0
        stars[i] = (sx, sy, size, spd)
        pygame.draw.circle(screen, (150, 150, 150), (int(sx + off_x*0.1), int(sy + off_y*0.1)), int(size))

    for p in particles[:]:
        if p.color == (60, 60, 60):
            p.update()
            if p.life <= 0: particles.remove(p)
            else: p.draw(screen, off_x, off_y)

    if game_state == "PLAYING" or game_state == "GAME_OVER":
        if not player.dead:
            wave_timer += 1
            spawn_threshold = max(15, 80 - (level * 4))
            if wave_timer > spawn_threshold:
                enemies.append(Enemy(random.randint(50, WIDTH - 80), -50, level))
                wave_timer = 0

            player.update(keys, mouse_pos, mouse_clicked, right_clicked)
            
            for p in powerups[:]:
                p.update()
                if p.dead: powerups.remove(p); continue
                
                if math.hypot(player.x - p.x, player.y - p.y) < 40 and not player.is_dashing:
                    if p.type == "HP":
                        heal = min(player.max_hp - player.hp, 20)
                        player.hp += heal
                        floating_texts.append(FloatingText(player.x, player.y - 30, f"+{heal} HP", HP_COLOR))
                        spawn_explosion(p.x, p.y, HP_COLOR, count=15)
                    elif p.type == "WEAPON":
                        player.weapon_boost_timer = 600
                        floating_texts.append(FloatingText(player.x, player.y - 30, "FIREPOWER UPGRADED!", WEAPON_COLOR))
                        spawn_explosion(p.x, p.y, WEAPON_COLOR, count=20)
                    elif p.type == "SHIELD":
                        player.shield_timer = 600
                        floating_texts.append(FloatingText(player.x, player.y - 30, "SHIELD ACTIVE!", SHIELD_COLOR))
                        spawn_explosion(p.x, p.y, SHIELD_COLOR, count=20)
                    powerups.remove(p)

            for e in enemies: 
                e.update()
                if not e.dead:
                    if math.hypot(player.x - e.x, player.y - e.y) < 45: 
                        if player.is_dashing or player.shield_timer > 0:
                            e.hp = 0
                            e.dead = True
                            add_shake(10)
                            vfx_color = P1_COLOR if player.is_dashing else SHIELD_COLOR
                            spawn_explosion(e.x, e.y, vfx_color, count=20, speed=6) 
                            
                            if player.is_dashing:
                                player.score += 150
                                floating_texts.append(FloatingText(e.x, e.y, "RAM KILL +150!", P1_COLOR))
                            else:
                                player.score += 50
                                floating_texts.append(FloatingText(e.x, e.y, "DEFLECTED!", SHIELD_COLOR))
                            
                            enemies_destroyed += 1
                        else:
                            player.hp -= 40 
                            e.hp = 0
                            e.dead = True
                            add_shake(15)
                            spawn_explosion(e.x, e.y, (255, 100, 50))
                            floating_texts.append(FloatingText(player.x, player.y, "CRASH! -40 HP", (255, 0, 0)))
                            if player.hp <= 0:
                                player.dead = True
                                spawn_explosion(player.x, player.y, player.color, count=50, speed=12)
                                save_score(user_name, player.score)
                                game_state = "GAME_OVER"
            
            for b in bullets[:]:
                b.update()
                if b.life <= 0: bullets.remove(b); continue
                
                if not b.is_enemy:
                    for e in enemies:
                        if not e.dead and math.hypot(b.x - e.x, b.y - e.y) < 25:
                            e.hp -= b.damage
                            if b in bullets: bullets.remove(b)
                            spawn_explosion(b.x, b.y, b.color, count=4, speed=3, shock=False) 
                            if e.hp <= 0:
                                e.dead = True
                                add_shake(3)
                                spawn_explosion(e.x, e.y, e.color)
                                
                                pts = 50 if e.type == "FIGHTER" else (100 if e.type == "SCOUT" else 200)
                                player.score += pts
                                floating_texts.append(FloatingText(e.x, e.y, f"+{pts}", WHITE))
                                
                                if not player.is_dashing:
                                    player.dash_energy = min(100, player.dash_energy + 20)

                                enemies_destroyed += 1
                                if enemies_destroyed % 10 == 0:
                                    level += 1
                                    level_display_timer = 120
                                    add_shake(10)
                                    floating_texts.append(FloatingText(player.x, player.y-50, "SYSTEM UPGRADED!", P1_COLOR))
                                
                                if random.random() < 0.25: 
                                    r_val = random.random()
                                    if r_val < 0.5: p_type = "HP"
                                    elif r_val < 0.8: p_type = "WEAPON"
                                    else: p_type = "SHIELD"
                                    powerups.append(PowerUp(e.x, e.y, p_type))
                            break
                else:
                    if not player.is_dashing and math.hypot(b.x - player.x, b.y - player.y) < 20:
                        if player.shield_timer > 0:
                            if b in bullets: bullets.remove(b)
                            spawn_explosion(b.x, b.y, SHIELD_COLOR, count=5, shock=False)
                        else:
                            player.hp -= b.damage
                            if b in bullets: bullets.remove(b)
                            add_shake(5)
                            spawn_explosion(b.x, b.y, (255, 50, 0), count=5, shock=False)
                            if player.hp <= 0:
                                player.dead = True
                                spawn_explosion(player.x, player.y, player.color, count=50, speed=10)
                                save_score(user_name, player.score)
                                game_state = "GAME_OVER"

            enemies = [e for e in enemies if not e.dead]
            
        for p in powerups: p.draw(screen, off_x, off_y)
        for b in bullets: b.draw(screen, off_x, off_y)
        for e in enemies: e.draw(screen, off_x, off_y)
        player.draw(screen, off_x, off_y)
        
        for p in particles[:]:
            if p.color != (60, 60, 60): 
                p.update()
                if p.life <= 0: particles.remove(p)
                else: p.draw(screen, off_x, off_y)
            
        for sw in shockwaves[:]:
            sw.update()
            if sw.life <= 0: shockwaves.remove(sw)
            else: sw.draw(screen, off_x, off_y)
            
        for ft in floating_texts[:]:
            ft.update()
            if ft.life <= 0: floating_texts.remove(ft)
            else: ft.draw(screen, mini_font, off_x, off_y)

        # --- HUD ---
        if not player.dead:
            score_text = score_font.render(f"SCORE: {player.score}  HP: {player.hp}", True, P1_COLOR)
            level_text = score_font.render(f"LEVEL: {level}  PILOT: {user_name}", True, WHITE)
            screen.blit(score_text, (20, 20))
            screen.blit(level_text, (20, 50))
            
            meter_x, meter_y = 80, HEIGHT - 90
            meter_radius = 45
            
            ability_lbl = mini_font.render("ULTIMATE", True, WHITE)
            screen.blit(ability_lbl, (meter_x - ability_lbl.get_width()//2, meter_y - meter_radius - 20))

            pygame.draw.circle(screen, (40, 40, 40), (meter_x, meter_y), meter_radius, 4)
            
            if player.dash_energy > 0:
                rect = pygame.Rect(meter_x - meter_radius, meter_y - meter_radius, meter_radius*2, meter_radius*2)
                stop_angle = math.pi / 2
                start_angle = math.pi / 2 - (player.dash_energy / 100.0) * 2 * math.pi
                pygame.draw.arc(screen, P1_COLOR, rect, start_angle, stop_angle, 6)
                
            if player.dash_energy >= 100:
                ready_txt = mini_font.render("READY", True, P1_COLOR)
                screen.blit(ready_txt, (meter_x - ready_txt.get_width()//2, meter_y - ready_txt.get_height()//2 - 10))
                btn_txt = mini_font.render("[SHIFT]", True, WHITE)
                screen.blit(btn_txt, (meter_x - btn_txt.get_width()//2, meter_y + 5))
            else:
                pct_txt = mini_font.render(f"{player.dash_energy}%", True, WHITE)
                screen.blit(pct_txt, (meter_x - pct_txt.get_width()//2, meter_y - pct_txt.get_height()//2))

            hud_y = 20
            if player.weapon_boost_timer > 0:
                boost_secs = player.weapon_boost_timer // 60
                boost_text = title_font.render(f"OVERDRIVE: {boost_secs}s", True, WEAPON_COLOR)
                screen.blit(boost_text, (WIDTH//2 - boost_text.get_width()//2, hud_y))
                hud_y += 50
                
            if player.shield_timer > 0:
                shield_secs = player.shield_timer // 60
                shield_text = title_font.render(f"SHIELD: {shield_secs}s", True, SHIELD_COLOR)
                screen.blit(shield_text, (WIDTH//2 - shield_text.get_width()//2, hud_y))

            bar_w, bar_h, bar_x, bar_y = 12, HEIGHT - 200, WIDTH - 30, 100
            pygame.draw.rect(screen, (40, 40, 40), (bar_x, bar_y, bar_w, bar_h), border_radius=6)
            progress = (enemies_destroyed % 10) / 10.0
            fill_h = int(bar_h * progress)
            fill_y = bar_y + bar_h - fill_h
            
            if fill_h > 0:
                pygame.draw.rect(screen, P1_COLOR, (bar_x, fill_y, bar_w, fill_h), border_radius=6)
                pygame.draw.circle(screen, WHITE, (bar_x + bar_w//2, fill_y), 8)
                
            lvl_lbl = mini_font.render(f"LVL {level+1}", True, WHITE)
            screen.blit(lvl_lbl, (bar_x - 20, bar_y - 25))
            
            if level_display_timer > 0:
                level_alert = title_font.render(f"LEVEL {level}", True, (255, 200, 0))
                level_alert.set_alpha(min(255, level_display_timer * 4))
                screen.blit(level_alert, (WIDTH//2 - level_alert.get_width()//2, HEIGHT//3))
                level_display_timer -= 1

            # In-Game Abort Button (Top Right)
            pygame.draw.rect(screen, (255, 100, 100), btn_in_game_menu, 2, border_radius=6)
            abort_txt = mini_font.render("ABORT", True, (255, 100, 100))
            screen.blit(abort_txt, (btn_in_game_menu.centerx - abort_txt.get_width()//2, btn_in_game_menu.centery - abort_txt.get_height()//2))

        if game_state == "GAME_OVER":
            s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            s.fill((0, 0, 0, 180))
            screen.blit(s, (0,0))
            
            over_title = title_font.render("SYSTEM FAILURE", True, (255, 50, 50))
            final_score = score_font.render(f"FINAL SCORE: {player.score} | REACHED LEVEL {level}", True, WHITE)
            screen.blit(over_title, (WIDTH//2 - over_title.get_width()//2, HEIGHT//2 - 160))
            screen.blit(final_score, (WIDTH//2 - final_score.get_width()//2, HEIGHT//2 - 90))

            pygame.draw.rect(screen, P1_COLOR, btn_same_pilot, 3, border_radius=10)
            screen.blit(menu_font.render("SAME PILOT", True, P1_COLOR), (btn_same_pilot.x + 65, btn_same_pilot.y + 15))

            pygame.draw.rect(screen, P1_COLOR, btn_new_pilot, 3, border_radius=10)
            screen.blit(menu_font.render("NEW PILOT", True, P1_COLOR), (btn_new_pilot.x + 75, btn_new_pilot.y + 15))

            pygame.draw.rect(screen, (255, 100, 100), btn_go_menu, 3, border_radius=10)
            screen.blit(menu_font.render("ABORT TO MENU", True, (255, 100, 100)), (btn_go_menu.x + 35, btn_go_menu.y + 15))

    elif game_state == "MENU":
        title = title_font.render("NOVA RIFT", True, P1_COLOR)
        sub = score_font.render("ULTIMATE EDITION", True, WHITE)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//3))
        screen.blit(sub, (WIDTH//2 - sub.get_width()//2, HEIGHT//3 + 70))

        pygame.draw.rect(screen, P1_COLOR, btn_play, 3, border_radius=10)
        screen.blit(menu_font.render("INITIATE DIVE", True, P1_COLOR), (btn_play.x + 40, btn_play.y + 15))

        pygame.draw.rect(screen, WHITE, btn_scores, 3, border_radius=10)
        screen.blit(menu_font.render("LEADERBOARD", True, WHITE), (btn_scores.x + 60, btn_scores.y + 15))

        pygame.draw.rect(screen, (255, 100, 100), btn_quit, 3, border_radius=10)
        screen.blit(menu_font.render("TERMINATE", True, (255, 100, 100)), (btn_quit.x + 70, btn_quit.y + 15))

        # --- Added specific credit text section as requested ---
        creator_text = mini_font.render("Created by Mohammed Faisal Pasha", True, (150, 150, 150))
        screen.blit(creator_text, (WIDTH//2 - creator_text.get_width()//2, HEIGHT - 50))

    elif game_state == "NAME_INPUT":
        prompt = title_font.render("IDENTIFY PILOT", True, P1_COLOR)
        screen.blit(prompt, (WIDTH//2 - prompt.get_width()//2, HEIGHT//3))
        
        cursor = "_" if (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        name_surface = title_font.render(user_name + cursor, True, WHITE)
        screen.blit(name_surface, (WIDTH//2 - name_surface.get_width()//2, HEIGHT//2))
        
        hint = score_font.render("(Press ENTER to Launch | ESC to Go Back)", True, (150, 150, 150))
        screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT//2 + 80))

    elif game_state == "HIGH_SCORES":
        title = title_font.render("HALL OF FAME", True, P1_COLOR)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 60))

        scores = load_scores()
        if len(scores) > 0:
            top_pilot = scores[0] 
            wish_text = score_font.render(f"🏆 BEST WISHES TO THE CHAMPION: {top_pilot['name']} ({top_pilot['score']} PTS)! 🏆", True, (255, 200, 0))
            screen.blit(wish_text, (WIDTH//2 - wish_text.get_width()//2, 130))

        max_scroll = max(0, (len(scores) * 40) - 400) 
        leaderboard_scroll = max(-max_scroll, min(0, leaderboard_scroll))
        
        list_rect = pygame.Rect(0, 200, WIDTH, 440)
        screen.set_clip(list_rect)

        y_offset = 220 + leaderboard_scroll
        for i, s in enumerate(scores):
            color = P1_COLOR if i == 0 else WHITE
            screen.blit(score_font.render(f"#{i+1}", True, color), (WIDTH//2 - 250, y_offset))
            screen.blit(score_font.render(f"{s['name']}", True, color), (WIDTH//2 - 100, y_offset))
            screen.blit(score_font.render(f"{s['score']} PTS", True, color), (WIDTH//2 + 150, y_offset))
            y_offset += 40

        screen.set_clip(None)
        
        if len(scores) > 11:
            scroll_hint = mini_font.render("(Scroll with Mouse Wheel or Up/Down Arrows)", True, (100, 100, 100))
            screen.blit(scroll_hint, (WIDTH//2 - scroll_hint.get_width()//2, 650))

        pygame.draw.rect(screen, (255, 100, 100), btn_back_scores, 3, border_radius=10)
        screen.blit(menu_font.render("BACK TO TERMINAL", True, (255, 100, 100)), (btn_back_scores.x + 10, btn_back_scores.y + 15))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()