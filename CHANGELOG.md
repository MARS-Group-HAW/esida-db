# Changelog

All notable changes to this project will be documented in this file. See [standard-version](https://github.com/conventional-changelog/standard-version) for commit guidelines.

### [0.2.2](https://github.com/MARS-Group-HAW/esida-db/compare/v0.2.1...v0.2.2) (2023-06-22)


### Features

* allow download of exact time point ([0fdf9db](https://github.com/MARS-Group-HAW/esida-db/commit/0fdf9db053c8d9d9b0378262225da426cc2946a6))
* **malariaatalas_mosnet:** implement new data layer ([909e85e](https://github.com/MARS-Group-HAW/esida-db/commit/909e85e953c5ea478b90700eb6761d88dbd13a4d))
* new propsecedu values, inverse to before ([6b60a19](https://github.com/MARS-Group-HAW/esida-db/commit/6b60a19c5e8432c6d2e7ba238bf6163b8e79dffe))
* signal input and overview ([33b69e6](https://github.com/MARS-Group-HAW/esida-db/commit/33b69e66d9fe2e3f94bc32e5ba9f8280627ea872))


### Bug Fixes

* **docker:** install postgresql-client after apt-get update ([76180f5](https://github.com/MARS-Group-HAW/esida-db/commit/76180f524f01b2e630cd48fc46e2efc1dbeb78b3))
* get time points orderd ([8d9ba6a](https://github.com/MARS-Group-HAW/esida-db/commit/8d9ba6a67d00c7380e46bbab3925446c75c6d8c2))
* **statcompiler_household:** manually append 2022 preliminary results ([ccea406](https://github.com/MARS-Group-HAW/esida-db/commit/ccea4064d3080293e2d7717f0b44b13360cbc5f9))
* **statcompiler:** use Mbeya values pre 2016 for Songwe ([91b380c](https://github.com/MARS-Group-HAW/esida-db/commit/91b380cc269dcc88400dab1a98c684f3c1d72f9d))
* **tnbs_medlabdens:** make sure only actual year is selected ([5aa9061](https://github.com/MARS-Group-HAW/esida-db/commit/5aa9061b5bb0fe3b917a95b9781cc10282675c4b))
* **tnbs_medlabdens:** wrong column name for technologists ([aeb5b98](https://github.com/MARS-Group-HAW/esida-db/commit/aeb5b988673f01fe2c38e4022eda4111f91d2923))
* wrong casting of ESIDA risk coordinates ([859e086](https://github.com/MARS-Group-HAW/esida-db/commit/859e0864a3eac52167b61a0e66bc948e4e955e6b))
* wrong parameter order ([f819419](https://github.com/MARS-Group-HAW/esida-db/commit/f8194199645b53785586164e8901dfaa1d98ae9d))

### [0.2.1](https://github.com/MARS-Group-HAW/esida-db/compare/v0.2.0...v0.2.1) (2023-05-29)


### Features

* algorithm with data range ([1699af6](https://github.com/MARS-Group-HAW/esida-db/commit/1699af60c7865cc042e20655ad1b63c907f6e482))
* allow download of shape type individually csv/excel ([ad87bde](https://github.com/MARS-Group-HAW/esida-db/commit/ad87bde28853d74e402f5c16ccafad8677015f19))
* basic visualizations for ESIDA risk scoring ([113f830](https://github.com/MARS-Group-HAW/esida-db/commit/113f830b2699762bc7cc737e7bbb9fd39d8dd0e8))
* literature based binary layers on TZA country level ([ee21384](https://github.com/MARS-Group-HAW/esida-db/commit/ee2138490b720c176650017bfe941bbd705aa62a))
* new aggregatet layers with proportions of education ([8999cd8](https://github.com/MARS-Group-HAW/esida-db/commit/8999cd868186fe2c7c065dbf34aec11f98b374bb))
* save resoning of algorithm datalayers to database ([a335640](https://github.com/MARS-Group-HAW/esida-db/commit/a33564082aee645a8ed82428b289ad51a38e7c13))
* select newer value if no older value is abailable ([8a791aa](https://github.com/MARS-Group-HAW/esida-db/commit/8a791aa19f062dcce4b7d6cd2ee837bc91a5c86c))
* show latest value with fallback on UI ([6db2a82](https://github.com/MARS-Group-HAW/esida-db/commit/6db2a82584a3f8ab305842c06f9044170bb90b29))
* simple week chart for signals ([04de581](https://github.com/MARS-Group-HAW/esida-db/commit/04de581c4bb40b73f55da424767c91155b7662cf))


### Bug Fixes

* **algorithm:** make sure to use Python date-types, so import is not np datetime64 ([68b58d4](https://github.com/MARS-Group-HAW/esida-db/commit/68b58d4b92e43cb53d42a567a77d4d0f77b14c61))
* catch wrogn date type (datetime64) during download ([c4cb51d](https://github.com/MARS-Group-HAW/esida-db/commit/c4cb51d386cc635a9c0283ddc0c67a45af8a42a6))
* check if layer is loaded before using it ([2cf5c64](https://github.com/MARS-Group-HAW/esida-db/commit/2cf5c64ef1470d41764c024bdf2a9b405804643a))
* cia_worldfactbook is not loadable ([cdd7d20](https://github.com/MARS-Group-HAW/esida-db/commit/cdd7d2067a577fe4060bd8ebe6c8c7ce30cb11cf))
* download option for parameter list ([7323f5c](https://github.com/MARS-Group-HAW/esida-db/commit/7323f5c145b87c8c489f950bf35854067ad1e3d4))
* **esida_localrisk:** hcavail tresholds, vectabund layer ([4db04d4](https://github.com/MARS-Group-HAW/esida-db/commit/4db04d4c71ef98e12363c452bc3e26558574e6ba))
* **esida_localrisk:** imlement factor for dual parameters ([e17b0be](https://github.com/MARS-Group-HAW/esida-db/commit/e17b0bec92b4bc74a57b493d4384d080589ac4b2))
* **esida_localrisk:** make sure there are no gaps in the thresholds ([74568a4](https://github.com/MARS-Group-HAW/esida-db/commit/74568a44c79e2fe59d935bb369afe70ca561e3c6))
* inferred download would break on no available data at all ([8251b53](https://github.com/MARS-Group-HAW/esida-db/commit/8251b53df24fe29abd5422832d64bbe4cd30ab1a))
* **meteostat:** in case of more than 3 stations in a shape the merge would fail ([f4cc7a7](https://github.com/MARS-Group-HAW/esida-db/commit/f4cc7a764d997d1a1d7c6d7c3ffe3be90fa206a3))
* on datalayer view set min/max date for chart date picker ([0814dea](https://github.com/MARS-Group-HAW/esida-db/commit/0814deacc77fe8f9c2553ce56ded3ab392857c91))
* only query API if date is actually set ([cd6be2f](https://github.com/MARS-Group-HAW/esida-db/commit/cd6be2f3f085507d189b1f268924508b76c27da6))
* parameter download duplicate name field during merge for inferred download ([4936ed3](https://github.com/MARS-Group-HAW/esida-db/commit/4936ed3d4afc8fcc84ef78cbbab376f0a863ac7a))
* provide json/wkt download instead of showing WKT directly on shape detail ([c44d1f7](https://github.com/MARS-Group-HAW/esida-db/commit/c44d1f7cf389ff87b16c77c6d49fbb99cb1a3d97))
* **riks:** likelihood thresholds inclusive values ([f1a0d47](https://github.com/MARS-Group-HAW/esida-db/commit/f1a0d470ddcdd41e333b1f1ab247179534ca636a))
* show icons for parameter loading state ([1861bbc](https://github.com/MARS-Group-HAW/esida-db/commit/1861bbc0d5ef9cf419fb8ef526e24ce2505fd978))
* wrong col selected for time_col=date ([9002ded](https://github.com/MARS-Group-HAW/esida-db/commit/9002ded430b240cdb9ed06e73ea2105b21d384cc))

## [0.2.0](https://github.com/MARS-Group-HAW/esida-db/compare/v0.1.0...v0.2.0) (2023-05-10)


### Features

* show version number in footer, implement changelog with standard-version ([3631a19](https://github.com/MARS-Group-HAW/esida-db/commit/3631a19dff164957031ffea30c03a1b7267cca2a))
