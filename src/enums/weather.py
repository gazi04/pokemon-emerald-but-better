from enum import StrEnum


class Weather(StrEnum):
    """Battle-wide weather. NONE means clear skies."""

    NONE = "none"
    SUN = "sun"  # harsh sunlight
    RAIN = "rain"
    SANDSTORM = "sandstorm"
    HAIL = "hail"
