# pyflowerpower
A collection of python scripts to support analyzing the FP sensor data structures.
Eventually, the analysis may allow for a cloud-less tool for sensor data retrieval.

## Requirements
For the BLE related scripts to work, the latest version of [bluepy](https://github.com/IanHarvey/bluepy)
is required, preferably installed with pip:
```
sudo -h pip install bluepy
```
Also, a fairly recent version of bluez (version 5.41 or above) is required.

## Scripts for sensor data analysis

### fp-download.py
Scan for available FP devices and read out live data or history data.

In lack of official documentation, the structure of the history data was derived by comparing 
downloaded raw data from a number of sensors. With some fields showing identical vales 
in all the files, not all of the data structure could be assigned. Also, there is not yet any sense 
to be made of the calibration data stored in the sensors.

Downloaded history data is saved to files named `hist-FPID-SID.dat` for further analysis, with
`FPID` being the short ID of the sensor (last two bytes in address) and `SID` being the session id.

The data comprises raw sensor data from which physical values can be calculated.
See [Sensordata.md](Sensordata.md) for details.

### fp-clouddata.py
Add matching cloud data to sensor history data for correlation analysis. Matching is done by timestamps.
Supports old and new cloud API via credential profiles. Note that for old and new API, separate
credentials are required.

For cloud API access, credentials must be supplied in a file `credentials.json` in form of a profile
(e.g. named "api1" or "api2"). A profile must specify a "method" with value "oldapi" or "newapi"
to choose the right API methods and the base URL of the API server.
See example `credentials.json.tmpl`.

One of the profile names specified in `credentials.json` must be passed to the script. For details, check
```
fp-clouddata.py -h
```

For any file with downloaded sensor data passed to the script, a new file named `comp-PROFILE-FPID-SID.dat`
will be created containing all session data for which cloud data could be retrieved.


## Supplementary scripts

### pylescanchar.py
Listen for available BTLE devices and try to read out their characteristics. 
Output is provided in mediawiki table format.

### pylescrape.py
Listen for advertisments and output advertised fields
