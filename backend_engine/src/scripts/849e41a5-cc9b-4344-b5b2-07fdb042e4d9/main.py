#!/bin/bash python3

import time
import random
import sys
from enum import Enum

class Outcome(Enum):
    RETRIABLE_ERROR = "RETRIABLE_ERROR"
    NON_RETRIABLE_ERROR = "NON_RETRIABLE_ERROR"
    SUCCESS = "SUCCESS"

def random_outcome():
    """
    Generates one of three outcomes:
      - Retriable error (~10%)
      - Non-retriable error (~0.1%)
      - Success (remaining ~89.9%)
    On success, sleeps for a random period between 1 and 5 seconds.
    
    Returns:
        Outcome: The enum indicating the outcome type.
    """
    r = random.random()  # random float in [0.0, 1.0)

    print("random number:")
    print(r)
    if r < 0.50:
        return Outcome.RETRIABLE_ERROR
    elif r < 0.50 + 0.001:
        return Outcome.NON_RETRIABLE_ERROR
    else:
        # Sleep between 1 and 5 seconds (uniformly distributed)
        time.sleep(random.uniform(1, 5))
        return Outcome.SUCCESS

res = random_outcome()
if res == Outcome.RETRIABLE_ERROR:
    print("RETRIABLE_ERROR")
    sys.exit(-1)
if res == Outcome.NON_RETRIABLE_ERROR:
    print("NON_RETRIABLE_ERROR")
    sys.exit(-1)

print(res)