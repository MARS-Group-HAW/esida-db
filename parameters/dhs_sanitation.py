import os
import re
import numpy as np
import pandas as pd

from esida.dhs_parameter import DHSParameter
from dbconf import get_engine

class dhs_sanitation(DHSParameter):

    def get_indicators(self):
        return ['WS_TLET_H_IMP' ]

    def consume(self, df):
        df[f'{self.parameter_id}'] = df[self.get_indicators()].mean(axis=1)
        self.df = df
