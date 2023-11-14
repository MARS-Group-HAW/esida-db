import os
import re
import numpy as np
import pandas as pd

from esida.dhs_parameter import DHSParameter
from dbconf import get_engine

class dhs_electricity(DHSParameter):

    def get_indicators(self):
        return ['HC_ELEC_P_ELC']

    def consume(self, df):
        df[self.parameter_id] = df[self.get_indicators()[0]]
        self.df = df
