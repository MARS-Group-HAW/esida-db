import os
import re
import numpy as np
import pandas as pd

from esida.statcompiler_parameter import StatcompilerParameter
from dbconf import get_engine

class statcompiler_electricity(StatcompilerParameter):

    def get_indicators(self):
        return ['HC_ELEC_P_ELC']

    def consume(self, df):
        #df[f'{self.parameter_id}_avg'] = df[self.get_indicators()].mean(axis=1)
        self.df = df
