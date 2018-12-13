"""
Utilities
"""


def percent_of(value, total):
    """
    Return an integer that is VALUE % of TOTAL
    """
    return int(100 * (value / float(total)))
