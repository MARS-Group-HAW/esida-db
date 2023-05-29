import random
import numpy as np
import pandas as pd
import functools

from esida.parameter import BaseParameter

class cia_worldfactbook(BaseParameter):

    def __init__(self):
        super().__init__()

        self.unemployment_rate = 10.3

        self.distributions = [
            {
                'from': 0,
                'to': 14,
                'prct': 42.7,
                'male': 12632772,
                'female': 12369115
            },
            {
                'from': 15,
                'to': 24,
                'prct': 20.39,
                'male': 5988208,
                'female': 5948134
            },
            {
                'from': 25,
                'to': 54,
                'prct': 30.31,
                'male': 8903629,
                'female': 8844180
            },
            {
                'from': 55,
                'to': 64,
                'prct': 3.52,
                'male': 954251,
                'female': 1107717
            },
            {
                'from': 65,
                'to': 99, # is this okay?
                'prct': 3.08,
                'male': 747934,
                'female': 1056905
            },
        ]
        self.weights = [d['prct']/100 for d in self.distributions]
        self.bins = [d['to'] for d in self.distributions]
        self.bins.insert(0, -1)
        self.labels = ["{}-{}".format(d['from'], d['to']) for d in self.distributions]

    def extract(self):
        # No machine parsable data provided.
        pass

    @functools.cached_property
    def is_loaded(self):
        return None


    def load(self, shapes=None, save_output=False, agent_count = None):

        print(agent_count)

        for shape in shapes:
            human_distr = np.random.choice(len(self.distributions), agent_count, p=self.weights)
            humans = []

            for d in human_distr:
                tpl = self.distributions[d]
                h = {}

                # gender
                total_pop_in_age_group = tpl['male'] + tpl['female']
                male_prop = tpl['male'] / total_pop_in_age_group

                if (random.random() > male_prop):
                    h['gender'] = 'Female'
                else:
                    h['gender'] = 'Male'

                # age
                h['age'] = random.randint(tpl['from'], tpl['to'])

                # Worker
                if (random.random() > (self.unemployment_rate/100)):
                    h['worker'] = True
                else:
                    h['worker'] = False

                # faith
                if (random.random() > 0.631):
                    h['faith'] = 'Muslim'
                else:
                    h['faith'] = 'Christian'

                #
                # Other MARS Specific columns
                #

                # partTimeWorker
                h['partTimeWorker'] = False

                h['averageSpeed'] = True
                h['speed'] = 0
                h['position'] = ''

                h['length'] = 0.22
                h['height'] = 1.7
                h['width'] = 0.46
                h['mass'] = 60

                humans.append(h)

            df = pd.DataFrame(humans)
            df.to_csv(self.get_output_path() / 'citizen_tanzania.csv', index=False)
