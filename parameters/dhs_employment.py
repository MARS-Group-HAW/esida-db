import os
import re
import numpy as np
import pandas as pd

from esida.dhs_parameter import DHSParameter
from dbconf import get_engine

class dhs_employment(DHSParameter):

    def get_indicators(self):
        return [
            'EM_EMPL_M_EMC',
            'EM_EMPL_M_ENC',
            'EM_EMPL_M_N12',
            'EM_EMPL_W_EMC',
            'EM_EMPL_W_ENC',
            'EM_EMPL_W_N12'
        ]

    def consume(self, df):
        df[f'{self.parameter_id}'] = df[self.get_indicators()].mean(axis=1)
        self.df = df
