
from esida.algorithm_parameter import AlgorithmParameter

class esida_risk_impact(AlgorithmParameter):

    def __init__(self):
        super().__init__()
        self.algorithm = 'input/algorithms/esida-risk-assessment-impact.yaml'

        self.precision = 0

        self.time_col = 'date'

        self.choropleth2 = [
            {
                'from':   7,
                'to':    10,
                'color': '#007502'
            },
            {
                'from':  11,
                'to':    14,
                'color': '#8DC500'
            },
            {
                'from':  15,
                'to':    18,
                'color': '#FFC500'
            },
            {
                'from':  19,
                'to':    21,
                'color': '#FF5B00'
            }
        ]
