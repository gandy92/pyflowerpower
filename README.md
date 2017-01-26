# pyflowerpower
pyflowerpower is a collection of python scripts to support analyzing the FP sensor data structures.
Eventually, the analysis may allow for a cloud-less tool for sensor data retrieval.


## Scripts for sensor data analysis

### fp-download.py
Scan for available FP devices and read out live data or history data.

In lack of official documentation, the structure of the history data was derived by comparing 
downloaded raw data from a number of sensors. With some fields showing identical vales 
in all the files, not all of the data structure could be assigned. Also, there is not yet any sense 
to be made of the calibration data stored in the sensors.

Downloaded history data is saved to files named `hist-FPID-SID.dat` for further analysis, with
`FPID` being the short ID of the sensor (last two bytes in address) and
`SID` being the session id.

### fp-clouddata.py
Add matching cloud data to sensor history data for correlation analysis.
Currently only works with the old cloud API.  Data retrieval from new
cloud API will be added as an alternative, not a replacement.

For cloud API access, credentials must be supplied in a file `credentials.json` in form of a profile
(e.g. named "oldapi" or "newapi" for the old and new cloud API, respectively). The credentials must specify
a "method" with value "oldapi" or "newapi" to choose the right API methods and the base URL of the API server. 
See example `credentials.json.tmpl`.

One of the profile names specified in `credentials.json` must be passed to the script. For details, check
```
fp-clouddata.py -h
```


## Supplementary scripts

### pylescanchar.py
Listen for available BTLE devices and try to read out their characteristics. 
Output is provided in mediawiki table format.

### pylescrape.py
Listen for advertisments and output advertised fields
