import os
import re
import numpy as np
import pandas as pd

from esida.statcompiler_parameter import StatcompilerParameter
from dbconf import get_engine

class statcompiler_drinkwater(StatcompilerParameter):

    def get_indicators(self):
        return ['WS_SRCE_H_IMP']

    def consume(self, df):
        self.df = df
