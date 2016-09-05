from __future__ import print_function

from time import gmtime, strftime
from bluepy.btle import Scanner, DefaultDelegate

class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        flags = 0
        flower = 0
        for (adtype, desc, value) in dev.getScanData():
            if adtype == 0xff:
                flags = value
            if adtype == 6 and value == '1bc5d5a50200baafe211a88400fae139':
                flower = 1
        if not flower:
            return
        #if isNewDev:
        print(strftime("%Y-%m-%d %H:%M:%S", gmtime()), "Discovered      device", dev.addr, "rssi:",dev.rssi, "flags:",flags)
        #elif isNewData:
        #    print(strftime("%Y-%m-%d %H:%M:%S", gmtime()), "Received new data from", dev.addr, "rssi:",dev.rssi, "flags:",flags))

scanner = Scanner().withDelegate(ScanDelegate())
devices = scanner.scan(100.0)

for dev in devices:
    print("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi))
    for (adtype, desc, value) in dev.getScanData():
        print("  %s = %s" % (desc, value))

