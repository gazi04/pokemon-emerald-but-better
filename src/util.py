import json


def get_configs():
    with open("data/config.json", "r") as f:
        return json.load(f)


def get_enc():
    with open("data/encounters.json", "r") as f:
        return json.load(f)


def calculate_multiplier(atk_type, def_types):
    with open("data/types.json", "r") as f:
        type_data = json.load(f)
    multiplier = 1.0
    for type in def_types:
        multiplier *= type_data.get(atk_type, {}).get(type, 1.0)
    return multiplier
