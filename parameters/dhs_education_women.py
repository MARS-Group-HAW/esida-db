from esida.dhs_parameter import DHSParameter

class dhs_education_women(DHSParameter):

    def get_indicators(self):
        return ['ED_EDUC_W_MYR']

    def consume(self, df):
        df[f'{self.parameter_id}'] = df[self.get_indicators()].mean(axis=1)
        self.df = df
