from esida.meteostat_parameter import MeteostatParameter

class meteo_rhum(MeteostatParameter):

    def __init__(self):
        super().__init__()
        self.meteo_mode = 'hourly' # do we need daily or hourly data?
        self.col_of_interest = 'rhum'
        self.is_percent = True
        self.is_percent100 = True

    def consume(self, df, shape):

        # resample hourly values to one day
        df = df.resample('d', on='time').mean(numeric_only=True).dropna(how='all')
        df = df.reset_index()

        # create mean for column of interest over all identified stations
        filter_col = [col for col in df if col.startswith(self.col_of_interest)]

        dfn = df[['time']]
        dfn = dfn.rename(columns={'time': 'date'})
        dfn['date'] = dfn['date'].dt.date # drop timestamp (hh:mm:ss) portion of date
        dfn['shape_id'] = shape['id']

        dfn[f'{self.parameter_id}']       = df[filter_col].mean(axis=1)
        dfn[f'{self.parameter_id}_std']   = df[filter_col].std(axis=1)
        dfn[f'{self.parameter_id}_min']   = df[filter_col].min(axis=1)
        dfn[f'{self.parameter_id}_max']   = df[filter_col].max(axis=1)
        dfn[f'{self.parameter_id}_count'] = df[filter_col].count(axis=1)

        dfn = dfn[dfn[f'{self.parameter_id}'].notna()]

        return dfn
