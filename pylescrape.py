from __future__ import print_function

from time import gmtime, strftime
from bluepy.btle import Scanner, DefaultDelegate, BTLEException
import json

class ScanDelegate(DefaultDelegate):
    def __init__(self, filename):
        DefaultDelegate.__init__(self)
        self.art = {}
        try:
            self.art = json.loads(open(filename).read())
        except:
            print("Could not load address table from file '%s'." % filename)
            pass

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
        print(strftime("%Y-%m-%d %H:%M:%S", gmtime()), 
              "Discovered      device", dev.addr, 
              "rssi:", dev.rssi, 
              "flags:", flags, self.resolv(dev.addr))
        #elif isNewData:
        #    print(strftime("%Y-%m-%d %H:%M:%S", gmtime()), "Received new data from", dev.addr, "rssi:",dev.rssi, "flags:",flags))

    def resolv(self, addr):
        if addr in self.art.keys():
            return self.art[addr]
        return ""

scanner = Scanner().withDelegate(ScanDelegate('addresstable.json'))
while 1:
    try:
        devices = scanner.scan(10.0)
    except BTLEException:
        print("---")
        pass
