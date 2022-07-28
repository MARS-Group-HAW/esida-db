from esida.meteostat_parameter import MeteostatParameter

class meteo_ahum(MeteostatParameter):

    def __init__(self):
        super().__init__()
        self.meteo_mode = 'hourly' # do we need daily or hourly data?
        self.col_of_interest = 'ahum'
        self.is_percent = True
        self.is_percent100 = True

    def consume(self, df, shape):

        def p_ws(T):
            """
            T in Celsius """

            # Constants in Temperature range of -20...+50°C
            A   = 6.116441
            m   = 7.591386
            T_n = 240.7263

            return A * 10 ** ((m * T) / (T + T_n))

        def p_w(T, rhum):
            """ Vapour pressure in Pa
            T in Celsius
            rhum in percent (i.e. 80.0)"""
            return p_ws(T) * (rhum / 100)


        def ahum(T, rhum):
            """ Absolute humidity, returns g/m3 air
            T in Celsius
            rhum in percent (i.e. 80.0)"""
            C = 2.16679 # gK/J

            return C * p_w(T, rhum) * 100 / (273.15 + T)

        # calc absolute humidity first
        temp_cols = [col for col in df if col.startswith('temp')]
        rhum_cols = [col for col in df if col.startswith('rhum')]

        if len(temp_cols) != len(rhum_cols):
            raise ValueError("Can't happen")

        for i in range(len(temp_cols)):
            df[f'ahum_{i}'] = df.apply(lambda x: ahum(x[temp_cols[i]], x[rhum_cols[i]]), axis=1)


        # resample hourly values to one day
        df = df.resample('d', on='time').mean().dropna(how='all')
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
