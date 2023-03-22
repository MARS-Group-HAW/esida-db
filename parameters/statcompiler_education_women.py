from esida.statcompiler_parameter import StatcompilerParameter

class statcompiler_education_women(StatcompilerParameter):

    def get_indicators(self):
        return ['ED_EDUC_W_MYR']

    def consume(self, df):
        df[f'{self.parameter_id}'] = df[self.get_indicators()].mean(axis=1)
        self.df = df
