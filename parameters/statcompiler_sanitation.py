import os
import re
import numpy as np
import pandas as pd

from esida.statcompiler_parameter import StatcompilerParameter
from dbconf import get_engine

class statcompiler_sanitation(StatcompilerParameter):

    def get_indicators(self):
        return ['WS_TLET_H_IMP' ]

    def consume(self, df):
        df[f'{self.parameter_id}_mean'] = df[self.get_indicators()].mean(axis=1)
        self.df = df
