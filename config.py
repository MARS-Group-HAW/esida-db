# config.py
# see: https://gist.github.com/ZacharyMcGuire/d81aa85409594a007fdf80e9fa9b329e
# returns a dictionary based on the provided section in the provided .ini file (defaults to database.ini and postgresql)
from configparser import ConfigParser


def config(filename='config.ini', section='postgis'):
    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(filename)

    # get section and update dictionary with connection string key:value pairs
    db = {}
    if section in parser:
        for key in parser[section]:
            db[key] = parser[section][key]
    else:
        raise Exception(
            'Section {0} not found in the {1} file'.format(section, filename))
    return db

# for debug purposes
if __name__ == '__main__':
    config()
