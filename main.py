# Scoring + HUD + optional popups + high score

import pygame
import random
import numpy as np
import os
import time

pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

# Load sound files
def load_sound(filename):
    try:
        sound_path = os.path.join('sound', filename)
        return pygame.mixer.Sound(sound_path)
    except:
        print(f"Could not load sound file: {filename}")
        return None

# Load the kill sound files
double_kill_sound = load_sound('doublekill.mp3')
triple_kill_sound = load_sound('triplekills.mp3')
monster_kill_sound = load_sound('monsterkill.mp3')
ouch_sound = load_sound('ouch.mp3')
gameover_sound = load_sound('gameover.mp3')

# Load level and win sounds
win_sound = load_sound('youwin.mp3')  # Use youwin.mp3 for victory

# Function to load level sound dynamically
def load_level_sound(level_num):
    return load_sound(f'level{level_num}.mp3')

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 100, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BROWN = (139, 69, 19)

FPS = 60
GRAVITY = 0.8
JUMP_SPEED = -18

# Scoring system constants
BASE_POINTS = 100                   # points per spider
CONSEC_BONUS_PER = 0.10             # +10% per consecutive-air kill beyond the first
MULTIKILL_MULTS = {1:1.0, 2:1.5, 3:2.0, 4:3.0}  # 4+ uses 3.0
COMBO_TIMEOUT_FRAMES = None         # set to an int (e.g., 90) to enable time-based combo reset; None to disable

def generate_kill_sound(pitch_multiplier=1.0):
    """Generate a simple beep sound with variable pitch"""
    duration = 0.1  # seconds
    sample_rate = 22050
    frequency = 440 * pitch_multiplier  # A4 note scaled by pitch
    
    frames = int(duration * sample_rate)
    arr = np.zeros((frames, 2))
    
    for i in range(frames):
        wave = np.sin(2 * np.pi * frequency * i / sample_rate)
        # Add envelope to prevent clicks
        envelope = min(i / (frames * 0.1), 1.0, (frames - i) / (frames * 0.1))
        arr[i] = [wave * envelope * 0.3, wave * envelope * 0.3]
    
    arr = (arr * 32767).astype(np.int16)
    sound = pygame.sndarray.make_sound(arr)
    return sound

def generate_multi_kill_sound(kill_count):
    """Generate a special chord sound for multi-kills"""
    duration = 0.3  # longer duration for impact
    sample_rate = 22050
    
    frames = int(duration * sample_rate)
    arr = np.zeros((frames, 2))
    
    # Create a chord with multiple frequencies based on kill count
    base_freq = 220  # Lower base frequency for richness
    frequencies = [base_freq * (1.0 + i * 0.25) for i in range(min(kill_count, 4))]  # Cap at 4 harmonics
    
    for i in range(frames):
        wave = 0
        for freq in frequencies:
            wave += np.sin(2 * np.pi * freq * i / sample_rate) / len(frequencies)
        
        # Create a decay envelope for dramatic effect
        envelope = max(0, 1.0 - (i / frames) ** 0.5) * 0.4
        arr[i] = [wave * envelope, wave * envelope]
    
    arr = (arr * 32767).astype(np.int16)
    sound = pygame.sndarray.make_sound(arr)
    return sound


def load_high_score():
    """Load high score from file, return 0 if file doesn't exist"""
    try:
        with open('highscore.txt', 'r') as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0

def save_high_score(score):
    """Save high score to file"""
    try:
        with open('highscore.txt', 'w') as f:
            f.write(str(score))
    except:
        pass  # Fail silently if can't write file

class Zach(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.blocks = 2  # Start with 2 blocks (2 lives)
        self.block_height = 20  # Height of each block
        self.max_blocks = 3  # Maximum number of blocks Zach can grow to
        self.update_sprite()
        self.rect.x = 100
        self.rect.bottom = SCREEN_HEIGHT - 60  # Position on ground like spiders
        self.vel_y = 0
        self.on_ground = False
        self.speed = 5
        self.consecutive_kills = 0
        self.invincible_timer = 0
        self.invincible_duration = 3 * FPS  # 3 seconds at 60 FPS
        self.just_lost_life = False  # Flag to prevent physics override after losing life
        self.ground_lock_timer = 0  # Timer to keep Zach locked to ground
    
    def update_sprite(self):
        """Update Zach's sprite based on current block count"""
        # Store current position before updating sprite
        old_bottom = getattr(self.rect, 'bottom', None) if hasattr(self, 'rect') else None
        
        total_height = self.blocks * self.block_height
        self.image = pygame.Surface((30, total_height))
        self.image.fill(BLUE)
        
        # Create new rect but preserve position if we had one
        new_rect = self.image.get_rect()
        if old_bottom is not None:
            # Maintain the same bottom position (ground level)
            new_rect.bottom = old_bottom
            new_rect.x = self.rect.x  # Also preserve x position
        else:
            # Initial setup - position on ground
            new_rect.bottom = SCREEN_HEIGHT - 60
            new_rect.x = 100
        
        self.rect = new_rect
        # Store the ground position for reference
        self.ground_y = SCREEN_HEIGHT - 60
    
    def add_life(self):
        """Add a life by increasing blocks by 1"""
        if self.blocks < self.max_blocks:
            self.blocks += 1
            self.update_sprite()
    
    def lose_life(self):
        """Lose a life by decreasing blocks by 1"""
        if self.blocks > 1:  # Minimum of 1 block
            self.blocks -= 1
            self.update_sprite()
            # Force Zach to be on the ground after losing a life
            self.reset_to_ground()
            return True  # Still alive
        else:
            return False  # Dead

    def update(self):
        # Update invincibility timer
        if self.invincible_timer > 0:
            self.invincible_timer -= 1
        
        # Update ground lock timer
        if self.ground_lock_timer > 0:
            self.ground_lock_timer -= 1
            # Force Zach to stay on ground while timer is active
            self._set_ground_position()
            # Allow horizontal movement even when locked to ground
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                self.rect.x -= self.speed
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                self.rect.x += self.speed
            return  # Skip vertical physics while locked to ground
        
        # Reset the just_lost_life flag after one frame
        if self.just_lost_life:
            self.just_lost_life = False
            # Force Zach to stay on ground for one more frame
            self._set_ground_position()
            return  # Skip physics update for one frame after losing life
        
        keys = pygame.key.get_pressed()
        
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.rect.x -= self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.rect.x += self.speed
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
            self.vel_y = JUMP_SPEED
            self.on_ground = False

        self.vel_y += GRAVITY
        self.rect.y += self.vel_y

        if self.rect.bottom >= SCREEN_HEIGHT - 60:
            self.rect.bottom = SCREEN_HEIGHT - 60
            self.vel_y = 0
            if not self.on_ground:  # Just landed
                self.consecutive_kills = 0  # Reset combo when landing
            self.on_ground = True

        if self.rect.x < 0:
            self.rect.x = 0
        if self.rect.x > SCREEN_WIDTH - 30:
            self.rect.x = SCREEN_WIDTH - 30

    def is_invincible(self):
        return self.invincible_timer > 0
    
    def start_invincibility(self):
        self.invincible_timer = self.invincible_duration
    
    def reset_to_ground(self):
        """Force Zach to be on the ground"""
        self._set_ground_position()
        self.just_lost_life = True  # Set flag to prevent physics override
        self.ground_lock_timer = 15  # Lock to ground for 15 frames (quarter second)
    
    def _set_ground_position(self):
        """Set Zach to ground position with proper physics state"""
        self.rect.bottom = SCREEN_HEIGHT - 60
        self.vel_y = 0
        self.on_ground = True

class Spider(pygame.sprite.Sprite):
    def __init__(self, x, y, level=1):
        super().__init__()
        self.image = pygame.Surface((25, 20))
        self.image.fill(RED)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        # Speed increases with level: base speed 1-3, +0.5 per level
        base_speed = random.randint(1, 3)
        level_bonus = (level - 1) * 0.5
        self.speed = base_speed + level_bonus
        self.direction = random.choice([-1, 1])

    def update(self):
        self.rect.x += self.speed * self.direction
        
        # Check boundaries and bounce back
        if self.rect.left <= 0:
            self.rect.left = 0
            self.direction *= -1
        elif self.rect.right >= SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
            self.direction *= -1

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Zach's Spider Adventure")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 74)
        self.small_font = pygame.font.Font(None, 36)
        self.level = 1
        
        # Scoring system state
        self.score = 0
        self.best_combo = 0
        self.high_score = load_high_score()
        self.combo_timer = 0
        self.floating_texts = []  # List of floating text popups
        
        # Track spiders defeated across all levels
        self.total_spiders_defeated = 0
        
        # Level transition state
        self.level_transition = False
        self.level_transition_start = 0
        self.level_transition_duration = 1.5  # seconds
        self.level_sound_played = False  # Track if level start sound has been played
        
        # Game completion state
        self.game_won = False
        
        self.reset_game()

    def reset_game(self):
        self.level = 1
        # Reset scoring state but preserve high score
        self.score = 0
        self.best_combo = 0
        self.combo_timer = 0
        self.floating_texts = []
        # Reset total spiders defeated when starting a new game
        self.total_spiders_defeated = 0
        # Reset level transition state
        self.level_transition = False
        self.level_sound_played = False
        # Reset game completion state
        self.game_won = False
        self.setup_level()
        # Play level start sound for level 1
        level_sound = load_level_sound(self.level)
        if level_sound:
            level_sound.play()

    def setup_level(self):
        self.zach = Zach()
        self.zach.start_invincibility()  # Start invincible for 3 seconds
        self.all_sprites = pygame.sprite.Group()
        self.spiders = pygame.sprite.Group()
        self.all_sprites.add(self.zach)
        
        for i in range(10):
            # Ensure spiders are spread out more evenly
            attempts = 0
            while attempts < 20:  # Try up to 20 times to find a good position
                x = random.randint(50, SCREEN_WIDTH - 50)
                y = SCREEN_HEIGHT - 80  # Position spiders on top of ground
                
                # Check if this position is too close to existing spiders
                too_close = False
                for existing_spider in self.spiders:
                    if abs(x - existing_spider.rect.x) < 50:  # Minimum 50 pixels apart
                        too_close = True
                        break
                
                if not too_close:
                    break
                attempts += 1
            
            spider = Spider(x, y, self.level)
            self.spiders.add(spider)
            self.all_sprites.add(spider)
        
        self.spiders_defeated = 0
        self.game_over = False
        self.zach_alive = True

    def next_level(self):
        self.level += 1
        # Start level transition
        self.level_transition = True
        self.level_transition_start = time.time()
        self.level_sound_played = False  # Reset sound flag for new level
    
    def check_level_transition(self):
        """Check if level transition is complete and setup new level if needed"""
        if self.level_transition:
            # Play level start sound if not already played
            if not self.level_sound_played:
                level_sound = load_level_sound(self.level)
                if level_sound:
                    level_sound.play()
                self.level_sound_played = True
            
            elapsed = time.time() - self.level_transition_start
            if elapsed >= self.level_transition_duration:
                self.level_transition = False
                self.setup_level()

    def handle_collisions(self):
        if not self.zach_alive:
            return
        
        # Skip collision detection if Zach is locked to ground (just lost life)
        if self.zach.ground_lock_timer > 0:
            return
            
        collisions = pygame.sprite.spritecollide(self.zach, self.spiders, False)
        
        if not collisions:
            return
            
        # Check all collisions first to see if any are kills vs damage
        spiders_to_kill = []
        zach_takes_damage = False
        
        for spider in collisions:
            zach_bottom = self.zach.rect.bottom
            spider_center_y = spider.rect.centery
            zach_falling = self.zach.vel_y > 0
            
            # Check if Zach is jumping on the spider from above
            if zach_bottom < spider_center_y + 10 and zach_falling:
                spiders_to_kill.append(spider)
            else:
                # Side or bottom collision - spider hurts/kills Zach
                zach_takes_damage = True
                break  # Even one side collision kills Zach
        
        if zach_takes_damage:
            if not self.zach.is_invincible():
                # Play ouch sound when Zach gets hurt
                if ouch_sound:
                    ouch_sound.play()
                
                # Zach loses a life from side collision
                if not self.zach.lose_life():
                    # Zach is dead (height reached 1 and lost another life)
                    if gameover_sound:
                        gameover_sound.play()
                    # Save high score on game over
                    if self.score > self.high_score:
                        self.high_score = self.score
                        save_high_score(self.high_score)
                    self.zach_alive = False
                    self.zach.kill()
                    self.game_over = True
                else:
                    # Zach survived but lost a life - start invincibility
                    self.zach.start_invincibility()
            # If invincible, Zach survives but no sound plays
        elif spiders_to_kill:
            # Kill all spiders Zach jumped on
            spiders_killed_count = len(spiders_to_kill)
            
            # Calculate average position for floating text popup
            avg_x = sum(spider.rect.centerx for spider in spiders_to_kill) // len(spiders_to_kill)
            avg_y = sum(spider.rect.centery for spider in spiders_to_kill) // len(spiders_to_kill)
            
            for spider in spiders_to_kill:
                spider.kill()
                self.spiders_defeated += 1
                self.total_spiders_defeated += 1
            
            # Calculate points awarded (using consecutive kills BEFORE this kill)
            consec_mult = 1.0 + CONSEC_BONUS_PER * max(0, self.zach.consecutive_kills)
            
            # Update consecutive kills counter AFTER calculating multiplier
            self.zach.consecutive_kills += spiders_killed_count
            multikey = min(spiders_killed_count, 4)
            multikill_mult = MULTIKILL_MULTS.get(multikey, MULTIKILL_MULTS[4])
            
            # Calculate base and total points
            base_points = BASE_POINTS * spiders_killed_count
            total_points = int(base_points * consec_mult * multikill_mult)
            bonus_points = total_points - base_points
            
            # Award points
            self.score += total_points
            self.best_combo = max(self.best_combo, self.zach.consecutive_kills)
            
            # Update high score and save if needed
            if self.score > self.high_score:
                self.high_score = self.score
                save_high_score(self.high_score)
            
            # Reset combo timer if enabled
            if COMBO_TIMEOUT_FRAMES is not None:
                self.combo_timer = COMBO_TIMEOUT_FRAMES
            
            # Add floating text popup only for bonus points
            if bonus_points > 0:
                self.floating_texts.append({
                    'text': f'+{bonus_points}',
                    'x': avg_x,
                    'y': avg_y,
                    'vy': -1.0,
                    'ttl': 30
                })
            
            # Play appropriate kill sound
            if spiders_killed_count == 2 and double_kill_sound:
                double_kill_sound.play()
            elif spiders_killed_count == 3 and triple_kill_sound:
                triple_kill_sound.play()
            elif spiders_killed_count >= 4 and monster_kill_sound:
                monster_kill_sound.play()
            else:
                # Single kill or fallback sound
                pitch = 1.0 + (self.zach.consecutive_kills - 1) * 0.2
                generate_kill_sound(pitch).play()
            
            # Play bonus sound for big multikill scoring
            if total_points >= BASE_POINTS * 3:
                generate_kill_sound(1.5).play()
            
            # Bounce height scales with number of spiders killed
            self.zach.vel_y = (JUMP_SPEED // 2) * spiders_killed_count
            
            if self.spiders_defeated >= 10:
                # Check if this is the final level (level 10)
                if self.level >= 10:
                    # Player has won the game!
                    self.game_won = True
                    self.game_over = True
                    # Play win sound
                    if win_sound:
                        win_sound.play()
                    # Save high score on game completion
                    if self.score > self.high_score:
                        self.high_score = self.score
                        save_high_score(self.high_score)
                else:
                    # Add a life when completing a level
                    self.zach.add_life()
                    self.next_level()

    def update_scoring(self):
        """Update scoring-related systems like combo timeout and floating text"""
        # Handle combo timeout
        if COMBO_TIMEOUT_FRAMES is not None and self.combo_timer > 0:
            self.combo_timer -= 1
            if self.combo_timer <= 0 and self.zach.consecutive_kills > 0:
                self.zach.consecutive_kills = 0  # Reset combo on timeout
        
        # Update floating text popups
        for text in self.floating_texts[:]:  # Use slice to avoid modifying list while iterating
            text['y'] += text['vy']
            text['ttl'] -= 1
            if text['ttl'] <= 0:
                self.floating_texts.remove(text)

    def draw(self):
        self.screen.fill(WHITE)
        
        pygame.draw.rect(self.screen, BROWN, (0, SCREEN_HEIGHT - 60, SCREEN_WIDTH, 60))
        
        # Draw all sprites except Zach (we'll draw him separately for blinking effect)
        for sprite in self.all_sprites:
            if sprite != self.zach:
                self.screen.blit(sprite.image, sprite.rect)
        
        # Draw Zach with blinking effect if invincible
        if self.zach_alive:
            if self.zach.is_invincible():
                # Blink every 5 frames (12 times per second at 60 FPS)
                if (pygame.time.get_ticks() // 83) % 2 == 0:  # 83ms = roughly 12Hz blink
                    self.screen.blit(self.zach.image, self.zach.rect)
            else:
                self.screen.blit(self.zach.image, self.zach.rect)
        
        # Left side HUD (existing)
        score_text = self.small_font.render(f"Spiders defeated: {self.total_spiders_defeated}", True, BLACK)
        self.screen.blit(score_text, (10, 10))
        
        level_text = self.small_font.render(f"Level: {self.level}", True, BLACK)
        self.screen.blit(level_text, (10, 50))
        
        # Right side HUD (new scoring system)
        score_display = self.small_font.render(f"Score: {self.score}", True, BLACK)
        score_rect = score_display.get_rect()
        score_rect.topright = (SCREEN_WIDTH - 10, 10)
        self.screen.blit(score_display, score_rect)
        
        high_score_display = self.small_font.render(f"High Score: {self.high_score}", True, BLACK)
        high_score_rect = high_score_display.get_rect()
        high_score_rect.topright = (SCREEN_WIDTH - 10, 50)
        self.screen.blit(high_score_display, high_score_rect)
        
        best_combo_display = self.small_font.render(f"Best Combo: {self.best_combo}", True, BLACK)
        best_combo_rect = best_combo_display.get_rect()
        best_combo_rect.topright = (SCREEN_WIDTH - 10, 90)
        self.screen.blit(best_combo_display, best_combo_rect)
        
        # Show current combo multiplier if active
        if self.zach.consecutive_kills > 0:
            consec_mult = 1.0 + CONSEC_BONUS_PER * max(0, self.zach.consecutive_kills - 1)
            combo_display = self.small_font.render(f"Combo x{consec_mult:.2f}", True, GREEN)
            combo_rect = combo_display.get_rect()
            combo_rect.topright = (SCREEN_WIDTH - 10, 130)
            self.screen.blit(combo_display, combo_rect)
        
        # Draw floating text popups
        for text in self.floating_texts:
            fade = text['ttl'] / 30.0
            alpha = int(255 * fade)
            color = (min(255, 100 + alpha), min(255, 50 + alpha), 0)
            text_surface = self.small_font.render(text['text'], True, color)
            x = text['x'] - text_surface.get_width() // 2
            self.screen.blit(text_surface, (x, int(text['y'])))
        
        if self.level_transition:
            # Draw level transition screen
            level_text = self.font.render(f"Level {self.level}", True, BLUE)
            text_rect = level_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2))
            self.screen.blit(level_text, text_rect)
            
            # Show countdown or progress
            elapsed = time.time() - self.level_transition_start
            remaining = max(0, self.level_transition_duration - elapsed)
            countdown_text = self.small_font.render(f"Starting in {remaining:.1f}s", True, BLACK)
            countdown_rect = countdown_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 80))
            self.screen.blit(countdown_text, countdown_rect)
        elif self.game_over:
            if self.game_won:
                # Show win screen
                win_text = self.font.render("YOU WIN!", True, GREEN)
                text_rect = win_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 50))
                self.screen.blit(win_text, text_rect)
                
                # Show final stats
                stats_text = self.small_font.render(f"Final Score: {self.score} | Total Spiders: {self.total_spiders_defeated}", True, BLACK)
                stats_rect = stats_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 10))
                self.screen.blit(stats_text, stats_rect)
                
                restart_text = self.small_font.render("Press 'R' to restart", True, BLACK)
                text_rect = restart_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 50))
                self.screen.blit(restart_text, text_rect)
            else:
                # Show game over screen
                lose_text = self.font.render("GAME OVER", True, RED)
                text_rect = lose_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 50))
                self.screen.blit(lose_text, text_rect)
                
                restart_text = self.small_font.render("Press 'R' to restart", True, BLACK)
                text_rect = restart_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 50))
                self.screen.blit(restart_text, text_rect)
        
        pygame.display.flip()

    def run(self):
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r and self.game_over:
                        self.reset_game()
            
            if not self.game_over:
                # Check for level transition completion
                self.check_level_transition()
                
                # Only update game if not in level transition
                if not self.level_transition:
                    # Update spiders separately from Zach to avoid interference
                    for sprite in self.all_sprites:
                        if sprite != self.zach:
                            sprite.update()
                    # Update Zach separately
                    self.zach.update()
                    # Update scoring systems
                    self.update_scoring()
                    self.handle_collisions()
            
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()