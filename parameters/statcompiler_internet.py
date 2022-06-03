import os
import re
import numpy as np
import pandas as pd

from esida.statcompiler_parameter import StatcompilerParameter
from dbconf import get_engine

class statcompiler_internet(StatcompilerParameter):

    def get_indicators(self):
        return ['CO_INUS_W_U12', 'CO_INUS_M_U12']

    def consume(self, df):
        df[f'{self.parameter_id}_mean'] = df[self.get_indicators()].mean(axis=1)
        self.df = df
