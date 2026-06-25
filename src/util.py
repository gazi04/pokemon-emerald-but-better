import json


def get_configs():
    with open("data/config.json", "r") as f:
        return json.load(f)
