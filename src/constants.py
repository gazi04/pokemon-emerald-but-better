TILE_SIZE = 32
MAP_HEIGHT = 1536
ENCOUNTER_RATE = 0.15
MOVE_DURATION = 0.2
PLAYER_MOVE_DURATION = 0.25  # player tile speed; NPCs use MOVE_DURATION (0.2)
TEXT_DELAY = 0.03
CAMERA_LERP_SPEED = 0.2
FLICKER_INTERVAL = 0.05
MAX_VISIBLE_ITEMS = 10
EVOLVE_IMAGE_SIZE = 200
BAG_UI = "assets/ui/bagUiDesign.tmx"
BATTLE_UI = "assets/ui/battleUiDesign.tmx"
EVOLVING_UI = "assets/ui/evolvingUiDesign.tmx"
DIALOG_UI = "assets/ui/dialog_ui_design.tmx"
POKEMON_INFORMATION_UI = "assets/ui/pokemon_info_ui_design.tmx"
POKEDEX_UI = "assets/ui/pokedex.tmx"
SHOP_UI = "assets/ui/shop_ui_design.tmx"
FONT = "assets/fonts/pokemon-emerald.otf"

CHANCE_TO_GET_ITEM = 0.3
ITEMS_FROM_PICK_UP = ["pokeball", "ether", "potion", "sitrus berry", "oran berry"]

# One tile step per facing direction. Arcade is y-up: "up" increases y.
DIRECTION_OFFSETS = {
    "up": (0, TILE_SIZE),
    "down": (0, -TILE_SIZE),
    "left": (-TILE_SIZE, 0),
    "right": (TILE_SIZE, 0),
}
OPPOSITE_DIRECTION = {"up": "down", "down": "up", "left": "right", "right": "left"}
