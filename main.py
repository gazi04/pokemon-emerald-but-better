import arcade
from data.config import Config
from src.core.game_director import GameDirector
from src.core.logger import configure_logging

CONFIG = Config.load()
configure_logging(CONFIG.logging)


def main():
    window = arcade.Window(
        width=CONFIG.window.width,
        height=CONFIG.window.height,
        title=CONFIG.window.title,
        fullscreen=CONFIG.window.fullscreen,
        resizable=CONFIG.window.resizable,
    )

    director = GameDirector(window)
    director.start()

    arcade.run()


if __name__ == "__main__":
    main()
