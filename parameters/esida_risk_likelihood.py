
from esida.algorithm_parameter import AlgorithmParameter

class esida_risk_likelihood(AlgorithmParameter):

    def __init__(self):
        super().__init__()
        self.algorithm = 'input/algorithms/esida-risk-assessment-likelihood.yaml'

        self.precision = 1

        self.time_col = 'date'

        self.choropleth = [
            {
                'from':   22,
                'to':    30.9,
                'color': '#007502'
            },
            {
                'from':  31,
                'to':    41.9,
                'color': '#8DC500'
            },
            {
                'from':  42,
                'to':    51.9,
                'color': '#FFC500'
            },
            {
                'from':  52,
                'to':    66,
                'color': '#FF5B00'
            }
        ]
