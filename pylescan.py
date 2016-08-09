from bluepy.btle import Scanner, DefaultDelegate, Peripheral, BTLEException
import binascii

class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            print "Discovered device", dev.addr
        elif isNewData:
            print "Received new data from", dev.addr

class MyDelegate(DefaultDelegate):
    def __init__(self, params):
        DefaultDelegate.__init__(self)
        # ... initialise here

    def handleNotification(self, cHandle, data):
        # ... perhaps check cHandle
        # ... process 'data'
	return


scanner = Scanner().withDelegate(ScanDelegate())
devices = scanner.scan(5.0)
ignore_char = [
  # '00002a00-0000-1000-8000-00805f9b34fb',
  '39e1fe02-84a8-11e2-afba-0002a5d5c51b'
]

for dev in devices:
    print "Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi)
    for (adtype, desc, value) in dev.getScanData():
        print "  %04x: %s = %s" % (adtype, desc, value)
    try:
        p = Peripheral(dev)
        p.setDelegate( MyDelegate(None) )
        for service in p.getServices():
            print "|  Service          || %s || || ||" % (service.uuid)
            print "|-"
            for char in service.getCharacteristics():
                data = ""
                if char.supportsRead():
                    if str(service.uuid) in ignore_char:
                        data = '(ignored service)'
                    elif str(char.uuid) in ignore_char:
                        data = '(ignored characteristic)'
                    else:
                        data = char.read()
                print "|    Characteristic || %s || %04x || %s || <%s>" % (char.uuid, char.properties, char.propertiesToString(), binascii.b2a_qp(data))
                print "|-"
    except BTLEException as e:
        print "got an BTLEException: "
