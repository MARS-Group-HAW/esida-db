from esida.statcompiler_parameter import StatcompilerParameter

class statcompiler_propsecedu_men(StatcompilerParameter):

    def get_indicators(self):
        return ['ED_EDUC_M_SSC', 'ED_EDUC_M_CSC', 'ED_EDUC_M_HGH']

    def consume(self, df):
        df[f'{self.parameter_id}'] = df[self.get_indicators()].sum(axis=1)
        self.df = df
