#!/usr/bin/python3

import requests
from datetime import *
from dateutil import parser
import json
from pprint import pformat
import string
import sys

SCRIPT = 'fp-clouddata.py v1.0'

debug = 0


def read_sensor_data_file(filename):
    params = {}
    data = []
    head = ""
    lines = open(filename).read().split('\n');
    print("Reading from %s..." % filename)
    for n, line in enumerate(lines):
        if len(line) < 1:
            continue
        if line[0] == '#':
            head += line + '\n'
            if ': ' in line:
                key, value = line[1:].strip().split(': ')
                params[key] = value
            elif ',' in line and '=' in line:
                for kv in line[1:].strip().split(','):
                    if '=' in kv:
                        key, value = kv.split('=')
                        params[key] = value
        else:
            dvec = line.split(' ')[8:14]
            if int(dvec[0]) == 0x8000:
                print("new session %d starts in line %d." % (int(dvec[1]), n))
                if len(data) > 0:
                    print("Dropping data from previous session with %d entries." % (len(data)))
                data = []
            data.append(dvec)

    return params, data, head


sens_id = sys.argv[1]
filename = 'hist-%s.dat' % sens_id
params, data, head = read_sensor_data_file(filename)
2 <= debug and print(pformat(params))
5 <= debug and print(pformat(data))
startup = int(params['current time']) - int(params['sensor time'])
last_ts = startup + int(params['lts'])
first_ts = last_ts - int(params['sp'])*(len(data)-1)


def fetch_cloud_samples(sens_id, from_ts, to_ts):
    # todo: create credentials.json if missing and exit with message to fill it in.
    credentials = json.loads(open('credentials.json').read())
    credentials['grant_type'] = 'password'

    req = requests.get('https://apiflowerpower.parrot.com/user/v1/authenticate', data=credentials)
    access_token = req.json()["access_token"]
    a_header = {'Authorization': 'Bearer ' + access_token}

    req = requests.get('https://apiflowerpower.parrot.com/sensor_data/v3/sync', headers=a_header)

    location_id = None
    for data in req.json()[u'locations']:
        if u'sensor_serial' in data:
            sens, loc = data[u'sensor_serial'], data[u'location_identifier']
            if sens[-len(sens_id):] == sens_id:
                location_id = loc

    if not location_id:
        print("Could not find location with sensor %s. Bailing out." % sens_id)
        return ()

    3 <= debug and print(location_id)
    i = 0
    # cloud sample timestamps are in utc
    ts_1 = datetime.utcfromtimestamp(from_ts)
    ts_e = datetime.utcfromtimestamp(to_ts)
    data = {}
    while ts_1 < ts_e:
        ts_2 = ts_1 + timedelta(days=7, seconds=-1)
        if ts_2 > ts_e:
            ts_2 = ts_e
        req = requests.get('https://apiflowerpower.parrot.com/sensor_data/v2/sample/location/' + location_id,
                           headers=a_header, params={'from_datetime_utc': ts_1,
                                                     'to_datetime_utc': ts_2})
        4 <= debug and print('Server response: \n {0}'.format(pformat(req.json())))
        ts_1 = ts_2
        for sample in req.json()['samples']:
            cts = sample['capture_ts']
            dt = parser.parse(cts)
            ts = int(dt.timestamp()) # - (datetime.now() - datetime.utcnow()).total_seconds())
            data[ts] = (sample['air_temperature_celsius'], sample['par_umole_m2s'], sample['vwc_percent'], cts)

    return data


cdata = fetch_cloud_samples(sens_id, first_ts-450, last_ts+450)
3 <= debug and print(pformat(cdata))

f = open('comp-%s.dat' % sens_id, 'w')
f.write('# Cloud samples collected by %s\n' % SCRIPT)
f.write(''.join(filter(lambda x: x in string.printable, head)))  # remove non-printable characters
f.write('#timestamp idx h0 h1 h2 h3 h4 h5 air_temp par vwc\n')

for ts in sorted(cdata.keys()):
    idx = int((ts - first_ts) / int(params['sp']) + 0.5)
    if 0 <= idx < len(data):
        2 <= debug and print(ts, idx, ' '.join(map(str, data[idx])), ' '.join(map(str, cdata[ts])))
        f.write('%d\t%d\t%s\t%s\n' % (ts, idx, '\t'.join(map(str, data[idx])), '\t'.join(map(str, cdata[ts]))))

f.close()

print('sensor data ranges starts at %s (ts=%d)' % (str(datetime.fromtimestamp(first_ts)), first_ts))
print('                 and ends at %s (ts=%d)' % (str(datetime.fromtimestamp(last_ts)), last_ts))

1 <= debug and print(datetime.utcnow())
1 <= debug and print(datetime.now())

