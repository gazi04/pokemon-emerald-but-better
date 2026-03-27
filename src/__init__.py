import arcade

# 1. Define Constants for easy adjustments
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "My Simple Arcade App"

class MyGame(arcade.Window):
    """ Main application class. """

    def __init__(self):
        # Call the parent class (arcade.Window) to create the window
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        
        # Set the background color
        arcade.set_background_color(arcade.color.SKY_BLUE)

    def setup(self):
        """ Set up the game variables here. """
        # This is where you would load your sprites, sounds, and maps
        pass

    def on_draw(self):
        """ Render the screen. """
        # Clear the screen to the background color
        self.clear()

        # Draw a simple circle (Center X, Center Y, Radius, Color)
        arcade.draw_circle_filled(400, 300, 50, arcade.color.YELLOW)
        
        # Draw some text
        arcade.draw_text("Hello Arcade!", 300, 200, arcade.color.WHITE, 24)

    def on_update(self, delta_time):
        """ Movement and game logic goes here. """
        # delta_time is the time since the last update (approx 1/60th of a sec)
        pass

def main():
    """ Main function """
    window = MyGame()
    window.setup()
    arcade.run()

if __name__ == "__main__":
    main()