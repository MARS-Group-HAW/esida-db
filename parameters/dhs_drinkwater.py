import os
import re
import numpy as np
import pandas as pd

from esida.dhs_parameter import DHSParameter
from dbconf import get_engine

class dhs_drinkwater(DHSParameter):

    def get_indicators(self):
        return ['WS_SRCE_H_IMP']

    def consume(self, df):
        df[self.parameter_id] = df[self.get_indicators()[0]]
        self.df = df
