from enum import Enum

class SearchTypeEnum(str, Enum):
    fuzzy_matching = "fuzzy"
    exact_matching = "exact"

class SearchThresholdEnum(str, Enum):
    fuzzy = 0.6
    exact = 0.8