import arcade


def parse_battle_layout(tilemap_path: str) -> dict:
    """
    Reads the Tiled map strictly to extract geometric data (rectangles, positions).
    Returns a unified dictionary of bounds instead of populating UI widgets.
    """
    tilemap = arcade.tilemap.load_tilemap(tilemap_path)
    bounds = {}

    raw_map_height = (
        tilemap.tiled_map.map_size.height * tilemap.tiled_map.tile_size.height
    )

    for layer in tilemap.tiled_map.layers:
        current_layer = tilemap.get_tilemap_layer(layer.name)

        for obj in current_layer.tiled_objects:
            w = int(obj.size.width / 32)
            h = int(obj.size.height / 32)
            x = int(obj.coordinates.x / 32)
            y = int((raw_map_height - obj.coordinates.y) / 32)

            bounds[obj.name] = {"x": x, "y": y, "w": w, "h": h}

    return bounds
