from esida.meteostat_parameter import MeteostatParameter

class meteo_dtr(MeteostatParameter):

    def __init__(self):
        super().__init__()

    def consume(self, df, shape):

        # get max of all available tmax col's
        filter_col = [col for col in df if col.startswith('tmax')]
        df['tmax_max'] = df[filter_col].max(axis=1)

        # get min of all available tmin col's
        filter_col = [col for col in df if col.startswith('tmin')]
        df['tmin_min'] = df[filter_col].max(axis=1)

        # remove all rows, where we have no max/min
        df = df[df['tmax_max'].notna() & df['tmin_min'].notna()]

        # create new dataframe for the shape with the dtr and shape/time information
        dfn = df[['time']]
        dfn = dfn.rename(columns={'time': 'date'})
        dfn['shape_id'] = shape['id']

        dfn[f'{self.parameter_id}'] = df['tmax_max'] - df['tmin_min']
        dfn[f'{self.parameter_id}_min'] = df['tmin_min']
        dfn[f'{self.parameter_id}_max'] = df['tmax_max']

        return dfn
