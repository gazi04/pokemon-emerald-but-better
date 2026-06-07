import arcade

class Npc(arcade.Sprite):
    def __init__(self, texture, x, y):
        super().__init__(texture, 1.9, x, y)
        
        