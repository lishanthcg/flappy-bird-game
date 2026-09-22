import pygame
import sys
import asyncio
import random
import math
from pathlib import Path

# ============================================================
# CONFIG
# ============================================================
GAME_WIDTH = 360
GAME_HEIGHT = 640
FPS = 60

BASE_DIR = Path(__file__).resolve().parent
HIGH_SCORE_FILE = BASE_DIR / "highscore.txt"
IS_WEB = sys.platform == "emscripten"
if IS_WEB:
    from platform import window as browser_window
HIGH_SCORE_KEY = "flappybird.highscore"

# Bird
BIRD_WIDTH = 34
BIRD_HEIGHT = 24
BIRD_X = GAME_WIDTH // 8
BIRD_START_Y = GAME_HEIGHT // 2

# Pipes
PIPE_WIDTH = 64
PIPE_HEIGHT = 512
PIPE_GAP = 160
PIPE_SPEED = -2.5
PIPE_INTERVAL = 1500  # milliseconds

# Physics
GRAVITY = 0.38
FLAP_POWER = -6.2
MAX_FALL_SPEED = 9.0

# Background animation
BACKGROUND_DURATION = 10.0   # each background lasts 10 seconds
TRANSITION_DURATION = 2.0    # last 2 seconds fade into the next background

# Game states
MENU = "menu"
PLAYING = "playing"
PAUSED = "paused"
GAME_OVER = "game_over"


# ============================================================
# HIGH SCORE
# ============================================================
def load_high_score():
    try:
        if IS_WEB:
            return max(0, int(browser_window.localStorage.getItem(HIGH_SCORE_KEY) or 0))
        return max(0, int(HIGH_SCORE_FILE.read_text().strip()))
    except Exception:
        return 0


def save_high_score(value):
    try:
        if IS_WEB:
            browser_window.localStorage.setItem(HIGH_SCORE_KEY, str(int(value)))
        else:
            HIGH_SCORE_FILE.write_text(str(int(value)))
    except Exception:
        # Storage may be blocked; the session's score still works.
        pass


# ============================================================
# PYGAME SETUP
# ============================================================
pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()

window = pygame.display.set_mode((GAME_WIDTH, GAME_HEIGHT))
pygame.display.set_caption("Flappy Bird Deluxe")
clock = pygame.time.Clock()



def load_sound(filename):
    if IS_WEB:
        filename = str(Path(filename).with_suffix(".ogg"))
    try:
        return pygame.mixer.Sound(str(BASE_DIR / filename))
    except (pygame.error, FileNotFoundError):
        return None


wing_sound = load_sound("wing.wav")
point_sound = load_sound("point.wav")
hit_sound = load_sound("hit.wav")
die_sound = load_sound("die_fixed.wav")
start_sound = load_sound("start.wav")

death_channel = None
if pygame.mixer.get_init():
    pygame.mixer.set_num_channels(8)
    pygame.mixer.set_reserved(2)
    death_channel = pygame.mixer.Channel(1)


def play_sound(sound):
    if sound:
        sound.play()


# ============================================================
# IMAGE LOADING
# ============================================================
def load_image(filename, size=None):
    path = BASE_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Missing image: {filename}\n"
            f"Put it in the same folder as this Python file."
        )

    image = pygame.image.load(str(path)).convert_alpha()

    if size is not None:
        image = pygame.transform.scale(image, size)

    return image


def load_optional_image(filename, fallback_image):
    path = BASE_DIR / filename

    if path.exists():
        image = pygame.image.load(str(path)).convert_alpha()
        return pygame.transform.scale(
            image,
            (GAME_WIDTH, GAME_HEIGHT)
        )

    return fallback_image


# Main/original daytime background
background_image = load_image(
    "flappybirdbg.png",
    (GAME_WIDTH, GAME_HEIGHT)
)

# Extra backgrounds
bg_evening = load_optional_image(
    "bg_evening.png",
    background_image
)

bg_late_sunset = load_optional_image(
    "bg_late_sunset.png",
    background_image
)

bg_early_night = load_optional_image(
    "bg_early_night.png",
    background_image
)

bg_sunrise = load_optional_image(
    "bg_sunrise.png",
    background_image
)

# Background order:
# Day -> Evening -> Late Sunset -> Early Night -> Sunrise -> Day ...
background_images = [
    background_image,
    bg_evening,
    bg_late_sunset,
    bg_early_night,
    bg_sunrise,
]

FULL_CYCLE = BACKGROUND_DURATION * len(background_images)

# Game images
bird_original = load_image(
    "flappybird.png",
    (BIRD_WIDTH, BIRD_HEIGHT)
)

top_pipe_image = load_image(
    "toppipe.png",
    (PIPE_WIDTH, PIPE_HEIGHT)
)

bottom_pipe_image = load_image(
    "bottompipe.png",
    (PIPE_WIDTH, PIPE_HEIGHT)
)


# ============================================================
# FONTS
# ============================================================
def font(size, bold=True):
    return pygame.font.SysFont("Arial", size, bold=bold)


title_font = font(44)
large_font = font(42)
medium_font = font(28)
small_font = font(18)
tiny_font = font(14)
retry_font_size = 20
retry_font = font(retry_font_size)
while retry_font.size("TRY AGAIN")[0] > 100 and retry_font_size > 12:
    retry_font_size -= 1
    retry_font = font(retry_font_size)


# ============================================================
# BIRD
# ============================================================
class Bird:
    def __init__(self):
        self.image = bird_original

        self.rect = self.image.get_rect(
            center=(
                BIRD_X + BIRD_WIDTH // 2,
                BIRD_START_Y
            )
        )

        self.velocity_y = 0.0
        self.angle = 0.0
        self.alive = True

    def reset(self):
        self.rect = self.image.get_rect(
            center=(
                BIRD_X + BIRD_WIDTH // 2,
                BIRD_START_Y
            )
        )

        self.velocity_y = 0.0
        self.angle = 0.0
        self.alive = True

    def flap(self):
        if self.alive:
            self.velocity_y = FLAP_POWER
            self.angle = 22

            play_sound(wing_sound)

    def update(self):
        self.velocity_y += GRAVITY

        self.velocity_y = min(
            self.velocity_y,
            MAX_FALL_SPEED
        )

        self.rect.y += int(self.velocity_y)

        # Bird tilts upward while flying up.
        if self.velocity_y < 0:
            self.angle = min(
                25,
                self.angle + 2
            )

        # Bird rotates downward while falling.
        else:
            self.angle = max(
                -85,
                self.angle - 3.5
            )

        # Stop bird leaving from top.
        if self.rect.top < 0:
            self.rect.top = 0
            self.velocity_y = 0

    def draw(self):
        rotated = pygame.transform.rotate(
            self.image,
            self.angle
        )

        rotated_rect = rotated.get_rect(
            center=self.rect.center
        )

        window.blit(
            rotated,
            rotated_rect
        )


# ============================================================
# PIPE PAIR
# ============================================================
class PipePair:
    def __init__(self):
        self.x = float(GAME_WIDTH + 20)

        gap_center = random.randint(
            190,
            GAME_HEIGHT - 190
        )

        top_bottom = (
            gap_center
            - PIPE_GAP // 2
        )

        bottom_top = (
            gap_center
            + PIPE_GAP // 2
        )

        self.top_rect = top_pipe_image.get_rect(
            bottomleft=(
                int(self.x),
                top_bottom
            )
        )

        self.bottom_rect = bottom_pipe_image.get_rect(
            topleft=(
                int(self.x),
                bottom_top
            )
        )

        self.passed = False

    def update(self):
        self.x += PIPE_SPEED

        self.top_rect.x = int(self.x)
        self.bottom_rect.x = int(self.x)

    def draw(self):
        window.blit(
            top_pipe_image,
            self.top_rect
        )

        window.blit(
            bottom_pipe_image,
            self.bottom_rect
        )

    def off_screen(self):
        return self.x + PIPE_WIDTH < 0


# ============================================================
# UI HELPERS
# ============================================================
def draw_text(
    text,
    used_font,
    color,
    center
):
    surface = used_font.render(
        str(text),
        True,
        color
    )

    rect = surface.get_rect(
        center=center
    )

    window.blit(
        surface,
        rect
    )

    return rect


def draw_shadow_text(
    text,
    used_font,
    center,
    main_color=(255, 255, 255)
):
    x, y = center

    draw_text(
        text,
        used_font,
        (40, 40, 40),
        (x + 2, y + 3)
    )

    return draw_text(
        text,
        used_font,
        main_color,
        center
    )


def draw_button(
    rect,
    text,
    mouse_pos,
    base=(82, 210, 35),
    used_font=medium_font
):
    hovered = rect.collidepoint(
        mouse_pos
    )

    color = (
        (105, 235, 45)
        if hovered
        else base
    )

    pygame.draw.rect(
        window,
        (35, 80, 20),
        rect.inflate(4, 4),
        border_radius=8
    )

    pygame.draw.rect(
        window,
        color,
        rect,
        border_radius=8
    )

    pygame.draw.line(
        window,
        (170, 255, 115),
        (
            rect.left + 8,
            rect.top + 8
        ),
        (
            rect.right - 8,
            rect.top + 8
        ),
        3
    )

    draw_shadow_text(
        text,
        used_font,
        rect.center
    )

    return hovered


def draw_panel(
    rect,
    color=(247, 218, 184)
):
    pygame.draw.rect(
        window,
        (73, 54, 28),
        rect.inflate(6, 6),
        border_radius=5
    )

    pygame.draw.rect(
        window,
        color,
        rect,
        border_radius=5
    )

    pygame.draw.rect(
        window,
        (255, 239, 211),
        rect.inflate(-12, -12),
        3
    )


def format_time(seconds):
    seconds = int(seconds)

    minutes = seconds // 60
    secs = seconds % 60

    return f"{minutes:02d}:{secs:02d}"


# ============================================================
# SMOOTH BACKGROUND TRANSITION
# ============================================================
def draw_animated_background(seconds):
    # Repeat forever.
    cycle_time = seconds % FULL_CYCLE

    # Current background number.
    current_index = int(
        cycle_time // BACKGROUND_DURATION
    )

    # Next background number.
    next_index = (
        current_index + 1
    ) % len(background_images)

    current_bg = background_images[
        current_index
    ]

    next_bg = background_images[
        next_index
    ]

    # Position inside current 10-second section.
    time_in_background = (
        cycle_time % BACKGROUND_DURATION
    )

    # Draw current background.
    window.blit(
        current_bg,
        (0, 0)
    )

    transition_start = (
        BACKGROUND_DURATION
        - TRANSITION_DURATION
    )

    # Fade during final 2 seconds.
    if time_in_background >= transition_start:
        progress = (
            time_in_background
            - transition_start
        ) / TRANSITION_DURATION

        # Smoothstep easing.
        progress = max(
            0.0,
            min(1.0, progress)
        )

        progress = (
            progress
            * progress
            * (3.0 - 2.0 * progress)
        )

        alpha = int(
            progress * 255
        )

        next_bg_fade = next_bg.copy()
        next_bg_fade.set_alpha(alpha)

        window.blit(
            next_bg_fade,
            (0, 0)
        )


# ============================================================
# GAME DATA
# ============================================================
bird = Bird()
pipes = []

score = 0
high_score = load_high_score()

game_state = MENU
game_over_time = 0
new_high_score = False

# Game timer
game_start_ticks = 0
elapsed_time = 0.0
elapsed_seconds = 0

# Pause timer
pause_started_ticks = 0
total_pause_ms = 0

# Pipe timer event
CREATE_PIPES = pygame.USEREVENT + 1

next_pipe_time = PIPE_INTERVAL / 1000.0

# Buttons
play_button = pygame.Rect(
    105,
    505,
    150,
    58
)

restart_button = pygame.Rect(
    190,
    488,
    122,
    52
)

home_button = pygame.Rect(
    48,
    488,
    122,
    52
)

pause_button = pygame.Rect(
    GAME_WIDTH - 52,
    14,
    38,
    38
)

resume_button = pygame.Rect(
    105,
    330,
    150,
    54
)

pause_home_button = pygame.Rect(
    105,
    395,
    150,
    54
)


# ============================================================
# GAME FUNCTIONS
# ============================================================
def reset_game():
    global next_pipe_time
    next_pipe_time = PIPE_INTERVAL / 1000.0
    global score
    global game_state
    global new_high_score

    global game_start_ticks
    global elapsed_time
    global elapsed_seconds

    global pause_started_ticks
    global total_pause_ms

    pipes.clear()
    bird.reset()

    score = 0
    new_high_score = False

    game_state = PLAYING

    game_start_ticks = pygame.time.get_ticks()

    elapsed_time = 0.0
    elapsed_seconds = 0

    pause_started_ticks = 0
    total_pause_ms = 0

    play_sound(
        start_sound
    )


def go_home():
    global score
    global game_state
    global new_high_score

    global elapsed_time
    global elapsed_seconds

    global pause_started_ticks
    global total_pause_ms

    pipes.clear()
    bird.reset()

    score = 0
    new_high_score = False

    game_state = MENU

    elapsed_time = 0.0
    elapsed_seconds = 0

    pause_started_ticks = 0
    total_pause_ms = 0


def pause_game():
    global game_state
    global pause_started_ticks

    if game_state == PLAYING:
        game_state = PAUSED

        pause_started_ticks = (
            pygame.time.get_ticks()
        )


def resume_game():
    global game_state
    global pause_started_ticks
    global total_pause_ms

    if game_state == PAUSED:
        if pause_started_ticks:
            total_pause_ms += (
                pygame.time.get_ticks()
                - pause_started_ticks
            )

        pause_started_ticks = 0
        game_state = PLAYING


def end_game():
    global game_state
    global high_score
    global new_high_score
    global game_over_time

    if game_state != PLAYING:
        return

    bird.alive = False
    game_state = GAME_OVER

    game_over_time = (
        pygame.time.get_ticks()
    )

    # Hit sound then death sound.
    if death_channel is not None:
        death_channel.stop()

        if hit_sound:
            death_channel.play(
                hit_sound
            )

            if die_sound:
                death_channel.queue(
                    die_sound
                )

        elif die_sound:
            death_channel.play(
                die_sound
            )

    # Save high score.
    if score > high_score:
        high_score = score
        new_high_score = True

        save_high_score(
            high_score
        )


# ============================================================
# DRAW MENU
# ============================================================
def draw_menu():
    window.blit(
        background_image,
        (0, 0)
    )

    # Floating bird animation.
    t = pygame.time.get_ticks() / 400

    bob_y = (
        275
        + math.sin(t) * 10
    )

    draw_shadow_text(
        "FLAPPY",
        title_font,
        (112, 145),
        (255, 225, 50)
    )

    draw_shadow_text(
        "BIRD",
        title_font,
        (255, 145),
        (110, 220, 75)
    )

    preview = pygame.transform.rotate(
        bird_original,
        math.sin(t * 1.3) * 8
    )

    preview_rect = preview.get_rect(
        center=(
            180,
            int(bob_y)
        )
    )

    window.blit(
        preview,
        preview_rect
    )

    draw_shadow_text(
        "HIGH SCORE",
        small_font,
        (290, 45)
    )

    draw_shadow_text(
        high_score,
        large_font,
        (290, 78)
    )

    hint_rect = pygame.Rect(
        95,
        350,
        170,
        48
    )

    pygame.draw.rect(
        window,
        (225, 72, 55),
        hint_rect,
        border_radius=8
    )

    pygame.draw.rect(
        window,
        (160, 45, 35),
        hint_rect,
        3,
        border_radius=8
    )

    draw_shadow_text(
        "TAP / SPACE",
        small_font,
        hint_rect.center
    )

    draw_shadow_text(
        "Fly through the pipes!",
        small_font,
        (
            GAME_WIDTH // 2,
            430
        )
    )

    mouse_pos = (
        pygame.mouse.get_pos()
    )

    draw_button(
        play_button,
        "PLAY",
        mouse_pos
    )


# ============================================================
# DRAW GAME
# ============================================================
def draw_game():
    # Smooth animated background.
    draw_animated_background(
        elapsed_time
    )

    # Pipes
    for pipe in pipes:
        pipe.draw()

    # Bird
    bird.draw()

    # Score
    draw_shadow_text(
        score,
        large_font,
        (
            GAME_WIDTH // 2,
            55
        )
    )

    # Timer
    draw_shadow_text(
        "TIME " + format_time(
            elapsed_seconds
        ),
        small_font,
        (80, 34)
    )

    # Pause button
    pygame.draw.rect(
        window,
        (45, 45, 55),
        pause_button,
        border_radius=8
    )

    pygame.draw.rect(
        window,
        (255, 255, 255),
        pause_button,
        2,
        border_radius=8
    )

    pygame.draw.rect(
        window,
        (255, 255, 255),
        (
            pause_button.x + 10,
            pause_button.y + 9,
            5,
            20
        )
    )

    pygame.draw.rect(
        window,
        (255, 255, 255),
        (
            pause_button.x + 23,
            pause_button.y + 9,
            5,
            20
        )
    )


# ============================================================
# DRAW PAUSE SCREEN
# ============================================================
def draw_pause_screen():
    draw_game()

    overlay = pygame.Surface(
        (
            GAME_WIDTH,
            GAME_HEIGHT
        ),
        pygame.SRCALPHA
    )

    overlay.fill(
        (0, 0, 0, 145)
    )

    window.blit(
        overlay,
        (0, 0)
    )

    draw_shadow_text(
        "PAUSED",
        large_font,
        (
            GAME_WIDTH // 2,
            235
        )
    )

    draw_text(
        "Game time is stopped",
        tiny_font,
        (235, 235, 235),
        (
            GAME_WIDTH // 2,
            282
        )
    )

    mouse_pos = (
        pygame.mouse.get_pos()
    )

    draw_button(
        resume_button,
        "RESUME",
        mouse_pos,
        base=(82, 210, 35)
    )

    draw_button(
        pause_home_button,
        "HOME",
        mouse_pos,
        base=(80, 145, 230)
    )

    draw_text(
        "Press P or ESC to continue",
        tiny_font,
        (255, 255, 255),
        (
            GAME_WIDTH // 2,
            475
        )
    )


# ============================================================
# DRAW GAME OVER
# ============================================================
def draw_game_over():
    draw_game()

    overlay = pygame.Surface(
        (
            GAME_WIDTH,
            GAME_HEIGHT
        ),
        pygame.SRCALPHA
    )

    overlay.fill(
        (0, 0, 0, 70)
    )

    window.blit(
        overlay,
        (0, 0)
    )

    game_over_font = font(34)

    draw_shadow_text(
        "GAME OVER",
        game_over_font,
        (
            GAME_WIDTH // 2,
            108
        ),
        (240, 65, 55)
    )

    panel = pygame.Rect(
        57,
        170,
        246,
        200
    )

    draw_panel(
        panel
    )

    draw_text(
        "SCORE",
        small_font,
        (60, 45, 35),
        (112, 205)
    )

    draw_text(
        "HIGH SCORE",
        small_font,
        (60, 45, 35),
        (248, 205)
    )

    draw_shadow_text(
        score,
        large_font,
        (112, 248)
    )

    draw_shadow_text(
        high_score,
        large_font,
        (248, 248)
    )

    if new_high_score:
        new_rect = pygame.Rect(
            205,
            282,
            72,
            24
        )

        pygame.draw.rect(
            window,
            (235, 70, 55),
            new_rect,
            border_radius=4
        )

        draw_text(
            "NEW!",
            tiny_font,
            (255, 255, 255),
            new_rect.center
        )

    # Medal
    if score >= 30:
        medal_color = (
            255,
            215,
            0
        )

        medal_name = "GOLD"

    elif score >= 15:
        medal_color = (
            205,
            205,
            205
        )

        medal_name = "SILVER"

    elif score >= 5:
        medal_color = (
            205,
            127,
            50
        )

        medal_name = "BRONZE"

    else:
        medal_color = (
            195,
            150,
            120
        )

        medal_name = "KEEP GOING"

    pygame.draw.circle(
        window,
        medal_color,
        (110, 315),
        22
    )

    draw_text(
        medal_name,
        tiny_font,
        (70, 45, 30),
        (225, 315)
    )

    draw_text(
        "TIME " + format_time(
            elapsed_seconds
        ),
        tiny_font,
        (70, 45, 30),
        (180, 345)
    )

    mouse_pos = (
        pygame.mouse.get_pos()
    )

    draw_button(
        home_button,
        "HOME",
        mouse_pos,
        base=(80, 145, 230)
    )

    draw_button(
        restart_button,
        "TRY AGAIN",
        mouse_pos,
        base=(82, 210, 35),
        used_font=retry_font
    )

    draw_text(
        "Press SPACE / UP / X to retry",
        tiny_font,
        (255, 255, 255),
        (
            GAME_WIDTH // 2,
            565
        )
    )


# ============================================================
# MAIN LOOP
# ============================================================
async def main():
    global score, pipes, elapsed_time, elapsed_seconds, next_pipe_time

    while True:
        for event in pygame.event.get():

            # Close game
            if event.type == pygame.QUIT:
                if not IS_WEB:
                    pygame.quit()
                return

            # Create pipes only when playing
            if (
                event.type == CREATE_PIPES
                and game_state == PLAYING
            ):
                pipes.append(
                    PipePair()
                )

            # ----------------------------------------------------
            # KEYBOARD
            # ----------------------------------------------------
            if event.type == pygame.KEYDOWN:

                # Pause / resume
                if event.key in (
                    pygame.K_p,
                    pygame.K_ESCAPE
                ):
                    if game_state == PLAYING:
                        pause_game()

                    elif game_state == PAUSED:
                        resume_game()

                    continue

                # Fly / start / restart
                if event.key in (
                    pygame.K_SPACE,
                    pygame.K_UP,
                    pygame.K_x
                ):

                    if game_state == MENU:
                        reset_game()
                        bird.flap()

                    elif game_state == PLAYING:
                        bird.flap()

                    elif game_state == GAME_OVER:
                        if (
                            pygame.time.get_ticks()
                            - game_over_time
                            > 450
                        ):
                            reset_game()
                            bird.flap()

            # ----------------------------------------------------
            # MOUSE
            # ----------------------------------------------------
            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
            ):

                # Pause button
                if (
                    game_state == PLAYING
                    and pause_button.collidepoint(
                        event.pos
                    )
                ):
                    pause_game()

                # Pause menu
                elif game_state == PAUSED:
                    if resume_button.collidepoint(
                        event.pos
                    ):
                        resume_game()

                    elif pause_home_button.collidepoint(
                        event.pos
                    ):
                        go_home()

                # Home/menu
                elif game_state == MENU:
                    if play_button.collidepoint(
                        event.pos
                    ):
                        reset_game()

                    else:
                        reset_game()
                        bird.flap()

                # Gameplay tap
                elif game_state == PLAYING:
                    bird.flap()

                # Game over buttons
                elif game_state == GAME_OVER:
                    if (
                        pygame.time.get_ticks()
                        - game_over_time
                        > 450
                    ):
                        if restart_button.collidepoint(
                            event.pos
                        ):
                            reset_game()

                        elif home_button.collidepoint(
                            event.pos
                        ):
                            go_home()

        # ========================================================
        # UPDATE
        # ========================================================
        if game_state == PLAYING:

            # Smooth floating-point game time.
            elapsed_time = (
                pygame.time.get_ticks()
                - game_start_ticks
                - total_pause_ms
            ) / 1000.0

            elapsed_seconds = int(
                elapsed_time
            )

            # Use active game time: SDL timers are unavailable in the browser.
            if elapsed_time >= next_pipe_time:
                pipes.append(PipePair())
                next_pipe_time = elapsed_time + PIPE_INTERVAL / 1000.0

            # Bird physics
            bird.update()

            # Pipes
            for pipe in pipes:
                pipe.update()

                # Score once per pipe pair.
                if (
                    not pipe.passed
                    and pipe.x + PIPE_WIDTH
                    < bird.rect.left
                ):
                    pipe.passed = True
                    score += 1

                    play_sound(
                        point_sound
                    )

                # Pipe collision
                if (
                    bird.rect.colliderect(
                        pipe.top_rect
                    )
                    or bird.rect.colliderect(
                        pipe.bottom_rect
                    )
                ):
                    end_game()
                    break

            # Remove old pipes
            pipes = [
                pipe
                for pipe in pipes
                if not pipe.off_screen()
            ]

            # Bird fell below screen
            if bird.rect.top > GAME_HEIGHT:
                end_game()

        # --------------------------------------------------------
        # GAME OVER FALLING ANIMATION
        # --------------------------------------------------------
        elif game_state == GAME_OVER:
            if bird.rect.bottom < GAME_HEIGHT - 5:
                bird.update()

            else:
                bird.rect.bottom = (
                    GAME_HEIGHT - 5
                )

                bird.velocity_y = 0
                bird.angle = -90

        # ========================================================
        # DRAW
        # ========================================================
        if game_state == MENU:
            draw_menu()

        elif game_state == PLAYING:
            draw_game()

        elif game_state == PAUSED:
            draw_pause_screen()

        elif game_state == GAME_OVER:
            draw_game_over()

        if game_state in (MENU, GAME_OVER):
            draw_shadow_text(
                "Create by Lishanth",
                tiny_font,
                (GAME_WIDTH // 2, GAME_HEIGHT - 30)
            )

        pygame.display.update()
        clock.tick(FPS)
        await asyncio.sleep(0)


asyncio.run(main())
