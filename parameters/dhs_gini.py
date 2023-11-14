from esida.dhs_parameter import DHSParameter

class dhs_gini(DHSParameter):

    def get_indicators(self):
        return ['HC_WIXQ_P_GNI']

    def consume(self, df):
        df[self.parameter_id] = df[self.get_indicators()[0]]
        self.df = df
