from esida.statcompiler_parameter import StatcompilerParameter

class statcompiler_gini(StatcompilerParameter):

    def get_indicators(self):
        return ['HC_WIXQ_P_GNI']

    def consume(self, df):
        self.df = df
