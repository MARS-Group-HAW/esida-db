
from esida.hdxhfr_parameter import HdxhfrParameter

class hdx_hfr_hospital(HdxhfrParameter):

    def __init__(self):
        super().__init__()

        self.facility_types = [
            'Hospital',
            'District Hospital',
            'Designated District Hospital',
            'Regional Referral Hospital',
            'Referral Hospital',
            'National Hospital',
        ]
