from esida.statcompiler_parameter import StatcompilerParameter

class statcompiler_propsecedu_women(StatcompilerParameter):

    def get_indicators(self):
        return ['ED_EDUC_W_SSC', 'ED_EDUC_W_CSC', 'ED_EDUC_W_HGH']

    def consume(self, df):
        df[f'{self.parameter_id}'] = df[self.get_indicators()].sum(axis=1)
        self.df = df
