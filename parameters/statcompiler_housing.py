from esida.statcompiler_parameter import StatcompilerParameter

class statcompiler_housing(StatcompilerParameter):

    def get_indicators(self):
        return ['HC_MEMB_H_MNM']

    def consume(self, df):
        self.df = df
