from esida.statcompiler_parameter import StatcompilerParameter

class statcompiler_household(StatcompilerParameter):

    def get_indicators(self):
        return ['HC_MEMB_H_MNM']

    def consume(self, df):
        df[self.parameter_id] = df[self.get_indicators()[0]]
        self.df = df
