from esida.dhs_parameter import DHSParameter

class dhs_propsecedu_women(DHSParameter):

    def get_indicators(self):
        return ['ED_EDUC_W_SSC', 'ED_EDUC_W_CSC', 'ED_EDUC_W_HGH']

    def consume(self, df):
        df[f'{self.parameter_id}'] = df[self.get_indicators()].sum(axis=1)
        self.df = df
