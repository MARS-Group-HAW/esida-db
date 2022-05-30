"""
STATcompiler Cellphone usage.
"""
from esida.statcompiler_parameter import StatcompilerParameter

class statcompiler_cellphone(StatcompilerParameter):

    def get_indicators(self):
        return ['CO_MOBB_W_MOB', 'CO_MOBB_M_MOB']

    def consume(self, df):
        df[f'{self.parameter_id}_sum'] = df[self.get_indicators()].sum(axis=1, min_count=1)
        df[f'{self.parameter_id}_avg'] = df[self.get_indicators()].mean(axis=1)

        self.df = df
