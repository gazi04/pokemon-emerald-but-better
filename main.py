import arcade
from src.states.overworld_view import OverworldView, CONFIG


def main():
    """Start the game"""
    window = arcade.Window(
        width=CONFIG.window.width,
        height=CONFIG.window.height,
        title=CONFIG.window.title,
        fullscreen=CONFIG.window.fullscreen,
        resizable=CONFIG.window.resizable,
    )

    start_view = OverworldView()
    window.show_view(start_view)
    arcade.run()


if __name__ == "__main__":
    main()
