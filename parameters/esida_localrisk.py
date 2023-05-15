import datetime as dt
import importlib

import pandas as pd
import osmnx as ox
import geopandas
import fiona
import yaml

from esida.parameter import BaseParameter
from dbconf import get_engine
from esida.models import Shape

class esida_localrisk(BaseParameter):

    def __init__(self):
        super().__init__()

        self.precision = 0


    def load(self, shapes=None, save_output=False):

        with open("input/algorithms/local-risk-assessment.yaml", "r") as stream:
            try:
                algorithm = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

        if shapes is None:
            shapes = self._get_shapes_from_db()

        self.rows = []
        log_rows = []

        for shape in shapes:
            shpobj = Shape.query.get(shape['id'])


            print("======")
            print(f"Shape-ID: {shape['id']}")
            print("")

            risk_score = 0
            for spec in algorithm['spec']:
                print(f"Checking: {spec['name']}")

                # check for multiple layers
                if spec.get('mode', None) == 'any':
                    datalayer_values = []

                    for datalayer in spec['datalayer']:
                        pm = importlib.import_module(f'parameters.{datalayer}')
                        dl = getattr(pm, datalayer)()
                        value = shpobj.get(datalayer, fallback_parent = True)

                        if value is not None and datalayer in value:
                            value = value[datalayer]

                        print(datalayer, value)

                        if value:
                            datalayer_values.append(value)

                    value = spec['value_no']
                    if len(datalayer_values) > 0:
                        value = spec['value_yes']
                else:
                    datalayer = spec['datalayer']
                    pm = importlib.import_module(f'parameters.{datalayer}')
                    dl = getattr(pm, datalayer)()

                    value = shpobj.get(spec['datalayer'], fallback_parent = True)

                    if value is not None and spec['datalayer'] in value:
                        value = value[spec['datalayer']]
                    else:
                        print("No dta available for shape/layer")
                        value = None
                    # in case the data layer is a count, but we need a proportion
                    # load the corresponding total data layer
                    if 'datalayer_total' in spec:
                        total = shpobj.get(spec['datalayer_total'])
                        total = total[spec['datalayer_total']]

                        value = value / total * 100

                    if dl.is_percent:
                        if not dl.is_percent100:
                            value = value * 100

                print(f"Datalayer value is: {value}")

                matching_thresh = None
                if value is not None:
                    for thresh in spec['thresholds']:

                        print(thresh)

                        # Check if is exact match
                        if "is" in thresh:
                            if thresh['is'] == value:
                                matching_thresh = thresh
                                break

                            continue

                        # Range checks
                        range_min = None
                        range_max = None

                        if 'min' in thresh:
                            range_min = thresh['min']
                        if 'max' in thresh:
                            range_max = thresh['max']

                        thresh['range_min'] = range_min
                        thresh['range_max'] = range_max

                        if 'inclusive' in thresh and thresh['inclusive'] is False:

                            if range_min is None:
                                if value < range_max:
                                    matching_thresh = thresh
                                    break
                            elif range_max is None:
                                if range_min < value:
                                    matching_thresh = thresh
                                    break
                            elif range_min < value < range_max:
                                matching_thresh = thresh
                                break
                        else:
                            if range_min is None:
                                if value <= range_max:
                                    matching_thresh = thresh
                                    break
                            elif range_max is None:
                                if range_min <= value:
                                    matching_thresh = thresh
                                    break
                            elif range_min <= value <= range_max:
                                matching_thresh = thresh
                                break
                else:
                    print("No data available for datalayer/shape")

                score = None

                factor = 1
                if "factor" in spec:
                    factor = spec['factor']

                if matching_thresh is None:
                    print("Datalayer value is outside of all ranges!")
                else:
                    print(f"matching: {matching_thresh}")
                    risk_score += matching_thresh['score'] * factor
                    score = matching_thresh['score'] * factor
                print("")

                row = {
                    'shape_id': shape['id'],
                    'shape_name': shape.get("name", ""),
                    'datalayer': spec['datalayer'],
                    'value': value,
                    'threshold_rule': matching_thresh,
                    'threshold_score': score,
                    'current_score': risk_score,
                }
                log_rows.append(row)

            self.rows.append({
                'shape_id': shape['id'],
                'year': 2023,
                'esida_localrisk': risk_score
            })

        self.set_output_path(f'output/{self.parameter_id}')
        log_df = pd.DataFrame(log_rows)
        log_df.to_csv(f"{self.get_output_path()}/{self.parameter_id}.csv")

        self.save()
