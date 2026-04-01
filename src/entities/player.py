import arcade
import random
from src.util import getPokemon

class Player(arcade.Sprite):
    def __init__(self, x: int, y: int):
        super().__init__(scale=2.0)
        
        # Load the full sheets
        idle_sheet = arcade.load_texture("assets/sprite/player/brendan_idle.png")
        walk_sheet = arcade.load_texture("assets/sprite/player/brendan_walk.png")
        
        # --- 1. Load Idle Textures Dynamically ---
        # 3 frames wide (Down, Up, Left), 1 frame tall
        i_w = idle_sheet.width // 3
        i_h = idle_sheet.height
        
        self.idle_textures = [
            idle_sheet.crop(0, 0, i_w, i_h),                       # Down
            idle_sheet.crop(i_w, 0, i_w, i_h),                     # Up
            # For the last frame, we calculate exactly what's left so we don't go out of bounds
            idle_sheet.crop(i_w * 2, 0, idle_sheet.width - (i_w * 2), i_h) # Left
        ]
        # Create Right by flipping Left
        self.idle_textures.append(self.idle_textures[2].flip_left_right())

        # --- 2. Load Walking Animation Dynamically ---
        # 2 frames wide (Down, Up), 2 frames tall (Step 1, Step 2)
        w_w = walk_sheet.width // 2
        w_h = walk_sheet.height // 2
        
        self.walk_textures_down = [
            walk_sheet.crop(0, w_h, w_w, walk_sheet.height - w_h), # Top frame
            walk_sheet.crop(0, 0, w_w, w_h)                        # Bottom frame
        ]
        
        self.walk_textures_up = [
            walk_sheet.crop(w_w, w_h, walk_sheet.width - w_w, walk_sheet.height - w_h), # Top
            walk_sheet.crop(w_w, 0, walk_sheet.width - w_w, w_h)                        # Bottom
        ]

        # Standard Setup
        self.texture = self.idle_textures[0]
        self.direction = "down"
        self.moving = False
        
        # Position
        self.center_x = x * 32 + 16
        self.center_y = y * 32 + 16
        self.target_x, self.target_y = self.center_x, self.center_y
        self.move_speed = 4.0
        
        self.anim_frame = 0
        self.anim_timer = 0

    def update(self, delta_time, keys, collision_tiles, bush):
        if self.moving:
            # --- Movement Logic ---
            if self.center_x < self.target_x: self.center_x += self.move_speed
            elif self.center_x > self.target_x: self.center_x -= self.move_speed
            if self.center_y < self.target_y: self.center_y += self.move_speed
            elif self.center_y > self.target_y: self.center_y -= self.move_speed

            # --- Animation Logic ---
            self.anim_timer += delta_time
            if self.anim_timer > 0.15:
                self.anim_timer = 0
                self.anim_frame = (self.anim_frame + 1) % 2
            
            # Update texture based on current direction
            if self.direction == "down":
                self.texture = self.walk_textures_down[self.anim_frame]
            elif self.direction == "up":
                self.texture = self.walk_textures_up[self.anim_frame]
            elif self.direction == "left":
                # If you don't have walk_textures_left yet, use idle_textures[2]
                self.texture = self.idle_textures[2]
            elif self.direction == "right":
                # Use the flipped idle texture (index 3)
                self.texture = self.idle_textures[3]

            # --- Snap to Target & Stop ---
            if abs(self.center_x - self.target_x) < self.move_speed and \
               abs(self.center_y - self.target_y) < self.move_speed:
                self.center_x, self.center_y = self.target_x, self.target_y
                self.moving = False
                
                # Reset to correct Idle Texture
                if self.direction == "down": self.texture = self.idle_textures[0]
                elif self.direction == "up": self.texture = self.idle_textures[1]
                elif self.direction == "left": self.texture = self.idle_textures[2]
                elif self.direction == "right": self.texture = self.idle_textures[3]
        
        else:
            new_dir = None
            dx, dy = 0, 0

            if arcade.key.UP in keys or arcade.key.W in keys:
                new_dir, dy = "up", 32
            elif arcade.key.DOWN in keys or arcade.key.S in keys:
                new_dir, dy = "down", -32
            elif arcade.key.LEFT in keys or arcade.key.A in keys:
                new_dir, dx = "left", -32
            elif arcade.key.RIGHT in keys or arcade.key.D in keys:
                new_dir, dx = "right", 32
            
            if new_dir:
                self.direction = new_dir
                
                # PRE-COLLISION CHECK
                target_x = self.center_x + dx
                target_y = self.center_y + dy
                
                # Find any sprites at the target position
                hit_list = arcade.get_sprites_at_point((target_x, target_y), collision_tiles)
                
                is_blocked = len(hit_list) > 0
                hit_bush = arcade.get_sprites_at_point((target_x, target_y), bush)
                
                if hit_bush:
                    pokemon_string = hit_bush[0].properties.get("pokemon")
                        
                    encounter_chance = random.random()
                        
                    if encounter_chance < 0.20:
                        possible_pokemon = [p.strip() for p in pokemon_string.split(",")]
                            
                        wild_pokemon = getPokemon()[random.choice(possible_pokemon)] 
                        print(f"Wild {wild_pokemon} appeared!")
                
                
                if not is_blocked:
                    self.moving = True
                    self.target_x = target_x
                    self.target_y = target_y
                else:
                    # Just change direction but don't move
                    self.moving = False
                    # Update idle texture to face the wall
                    if self.direction == "down": self.texture = self.idle_textures[0]
                    elif self.direction == "up": self.texture = self.idle_textures[1]
                    elif self.direction == "left": self.texture = self.idle_textures[2]
                    elif self.direction == "right": self.texture = self.idle_textures[3]

    def draw(self):
        arcade.draw_sprite(self)
        
    def getPosition(self):
        return (self.center_x, self.center_y)