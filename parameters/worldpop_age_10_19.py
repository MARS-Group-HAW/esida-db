import re
import os
import subprocess
import datetime as dt
from urllib.parse import urlparse

import numpy as np
import pandas as pd

from esida.sexage_parameter import SexageParameter

class worldpop_age_10_19(SexageParameter):

    def __init__(self):
        super().__init__()
        self.ages = [10, 15]
