# Sensordata
This document describes the structure of the sensor history file and show how the raw data could be converted to
physical values.

## The history data file
The history data file kept in the sensor is downloaded through the history service characteristic 0x39e1FC00.
The download procedure is documented in detail in the file FlowerPower-BLE.pdf.  The strucutre of the downloaded
data however is not documented, so everything that follows is based on assumuptions.

### general history data layout
Comparing history files with different numbers of entries shows that the file comprises
* a 16 byte header followed by
* *n* x 12 byte measurement data

Measurement data is grouped in sessions (identified by *SID*). Within a session, a new entry with measurement data
is saved at a constant rate given by the *session period* (default: 900 seconds).
A new session starts after battery replacement and presumably after a change of the session period (although there
is no characteristic indicating a means to do so).

Comparing various history files from different sensors yields more detailed information, with all 2- and 4-byte
values in MSB order:

#### Header fields
* Byte 0,1: *(Yet unknown)*
* Byte 2,3: Number of entries *n*
* Byte 4,5,6,7: Last entry timestamp (sensor time)
* Byte 8,9,10,11: Last entry index (over all sessions)
* Byte 12,13: Session id
* Byte 14,15: Session period (seconds)

Note: The session referred to in the header appears to be the currently active session in the sensor.

#### Measurement entry fields
An entry starting with 0x8000 marks a new session:
* Byte 0,1: 0x8000, session marker
* Byte 2,3: New session ID (*SID*)
* Byte 4,5: Session period (seconds)
* Byte 6-11: Apparently all zero

All entries not starting with 0x8000 contain actual measurement data.

The following table shows assumptions based on sensor data taken with firmware 1.1.1, compared to converted data
downloaded through the old cloud API:

Field | Byte | Physical entity  | Life-Char. | Conversion               | Remarks
------|------|------------------|------------|--------------------------|-----------------------
  1  | 0,1   | air temperature  | 0x39e1FA04 | 3rd order polynom        | same coefficients for all sensors
  2  | 2,3   | light level      | 0x39e1FA01 | power function           | sensor specific scaling
  3  | 4,5   | (soil EC)        | 0x39e1FA02 | electrical conductivity  | obviously temperature dependent
  4  | 6,7   | soil temperature | 0x39e1FA03 | same as air temperature? |
  5  | 8,9   | (soil VWC)       | 0x39e1FA05 | volumetric water content | apparently temperature dependent
  6  | 10,11 | battery-Level    | 0x2A19     | linear function          | same coefficients for all sensors

For some of the data fields, simple conversion functions can be fitted to sample points comprising cloud values
and raw values.

## Data interpreted using the old cloud API
### Air temperatures (old cloud API)
Air temperature values (*y*) correlate to values from data field 1 (x) by cubic function:
```
y = -29.51 + 0.1149 * x - 8.038e-05 * x^2 + 3.044e-08 * x^3
```

### Soil temperature (old cloud API)
For soil temperature, the same conversion function as for air temperature may be valid.

### Light sensor (old cloud API)
Light level in terms of *PAR* (Photosynthetically Active Radiation, 400nm - 700nm) can be calculated from data field 2
by applying a power function
```
y = a / y^1.0607
```
Or in linear form, with `X=ln(x)`, `Y=ln(y)` and A=ln(a):
```
Y = A - y*1.0607
```
A is sensor-dependent and can be calculated by reading out the uncalibrated and calibrated values through their
BLE characteristics of the *Life Service*:
* 0x39e1fa01 (uint16): Light sensor value
* 0x39e1fa0b (float32): Calibrated DLI

These values can be read out easily with
```
./fp-download.py --addr ADDR --light
```

The [official documentation thread](http://forum.developer.parrot.com/t/docs-sensors-informations/94) from the
Parrot-forum yields additional information:
* the lightsensor is calibrated to *PAR* (Photosynthetically Active Radiation, 400nm - 700nm). Typical units are
    * the *DLI* (Daily Light Integral) ranging between 0.13 (very dark) und 104 mol/m²d, and
    * the instantaneous PAR in µmol/m²s, usually displayed by portable instruments
* the *instantaneous PAR* value in *µmol/m²s* is converted from *DLI* by multiplication with `1000000 / (24 * 60 * 60)`
  (roughly 11.574) and ranges between 0 (dark) and 1200 (direct summer sun).
* the *instantaneous PAR* value in Lux (Lumen/m²) is converted from *µmol/m²s* by multiplication with 53.93
  (approximation based on spectral assumptions).

### Battery level (old cloud API)
The old cloud api does not yield battery level data. For correlation, battery levels were read our manually through the
*Life Servie*. A linear correlation is found:
```
y = -210.84 + 0.32269 * x
```
or roughly approximated:
```
y = (x - 653) / 3.1
```

### Soil humidity (old cloud API)
For calculation of the soil moisture, more than one of the raw data fields are required.
The nature of the conversion function depends on how the sensor determines the soil moisture, in the first place.

The [sensors informations](http://forum.developer.parrot.com/t/docs-sensors-informations/94/3) in the Parrot-forum
yields the following general information:
* Range: 0 to 50 (%)
* The typical soil moisture range is between 8 (very dry) to 45 (saturated).
* The soil moisture will read 0 when in air.
* Generally, most plants require watering when the soil moisture is in the range of 12 to 18.
* If the soil moisture stays > 40 for too long, this may be harmful to some plants (overwatering promotes the growth
  of pathogens in the soil, and plants require oxygen at their roots for good health).
* Specific watering and overwatering thresholds depend on the plant type.

Finding a valid conversion function however requires more detailed understanding of the measurement principles.
The sensor shows a forked geometry with no obviously conducting interfaces and two conducting knobs at the base
of the fork near the plastic housing.
This general makeup may be consistent with a frequency based measurement of the soil dielectric constant in
combination with a conductivity measurement.
Incidentally, firmware 1.1.1 showed BLE characteristics for reading out *calibrated EA*, *ECB* and *EC porous*.
These characteristics vanished with later firmware versions.

### Fertilizer level (old cloud API)
Calculation of the fertilizer level may be even more complex than in the case of soil humidity. Inspecting cloud data
shows a possible influence of watering cycles: Fertilizer levels appear to be updated some time after a plant was
watered.

## Data interpreted using the new cloud API
With introduction of the new cloud service accompanying the new firmware version 2.0.1, plant watering
recommendations and sensor data conversion have changed. The new cloud service also stores additional
sensor values

To be continued...
