import re
import os
import datetime as dt

import numpy as np

from esida.copernicus_parameter import CopernicusParameter


class copernicus_crop(CopernicusParameter):

    def __init__(self):
        super().__init__()

        self.area_of_interest = [
            'cropland'
        ]
