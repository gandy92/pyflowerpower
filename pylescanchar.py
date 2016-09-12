from __future__ import print_function

from bluepy.btle import Scanner, DefaultDelegate, Peripheral, BTLEException
import binascii
import struct


class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            print("Discovered device", dev.addr)
        elif isNewData:
            print("Received new data from", dev.addr)

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

uuids = {
  0x1800: { 'desc': "GAP Service", 'page': 24 },
  0x2A00: { 'service': 0x1800, 'desc': "Name", 'type': 'UTF8', 'page': 24 },
  0x2A01: { 'service': 0x1800, 'desc': "Appearance", 'type': 'U16', 'page': 24 },
  # undocumented
  0x2A02: { 'service': 0x1800, 'desc': "Peripheral Privacy Flag", 'type': 'U8' },
  0x2A03: { 'service': 0x1800, 'desc': "Reconnection Address", 'type': 'U8*12' },
  0x2A04: { 'service': 0x1800, 'desc': "Peripheral Preferred Connection Parameters", 'type': 'U8*16' },

  # undocumented
  0x1801: { 'desc': "Generic Attribute" },
  0x2A05: { 'service': 0x1801, 'desc': "Service Changed", 'type': '??' },

  0x180A: { 'desc': "Device Information", 'page': 24 },
  0x2A23: { 'service': 0x180A, 'desc': "System ID", 'type': 'U8*8', 'page': 24 },
  0x2A26: { 'service': 0x180A, 'desc': "Firmware revision", 'type': 'UTF8', 'page': 24 },
  0x2A25: { 'service': 0x1800, 'desc': "Serial number", 'type': 'UTF8', 'page': 24 },
  0x2A27: { 'service': 0x1800, 'desc': "Hardware revision", 'type': 'UTF8', 'page': 24 },
  # undocumented
  0x2A24: { 'servcie': 0x1800, 'desc': "Model Number String", 'type': 'UTF8' },
  0x2A28: { 'service': 0x180A, 'desc': "Software Revision String", 'type': 'UTF8' },
  0x2A29: { 'service': 0x180A, 'desc': "Manufacturer Name String", 'type': 'UTF8' },
  0x2A2A: { 'service': 0x180A, 'desc': "Certification Data List", 'type': '??' },
  0x2A50: { 'service': 0x180A, 'desc': "PnP ID", 'type': '' },

  # undocumented
  0x180F: { 'desc': "Battery Service" },
  0x2A19: { 'service': 0x180F, 'desc': "Battery Level", 'type': 'U8' },

  0x39e1FA00: { 'desc': "Live Service", 'page': 25 },
  0x39e1FA01: { 'service': 0x39e1FA00, 'desc': "Light sensor value", 'type': 'U16', 'page': 25 },
  0x39e1FA02: { 'service': 0x39e1FA00, 'desc': "Soil EC", 'type': 'U16', 'page': 25 },
  0x39e1FA03: { 'service': 0x39e1FA00, 'desc': "Soil temperature", 'type': 'U16', 'page': 25 },
  0x39e1FA04: { 'service': 0x39e1FA00, 'desc': "Air temperature", 'type': 'U16', 'page': 25 },
  0x39e1FA05: { 'service': 0x39e1FA00, 'desc': "Soil % VWC", 'type': 'U16', 'page': 25 },
  0x39e1FA06: { 'service': 0x39e1FA00, 'desc': "Live measure period", 'type': 'U8', 'page': 25 },
  0x39e1FA07: { 'service': 0x39e1FA00, 'desc': "LED state", 'type': 'U8', 'page': 25 },
  0x39e1FA08: { 'service': 0x39e1FA00, 'desc': "Last move date", 'type': 'U32', 'page': 25 },
  # FW version >= 1.0.0
  0x39e1FA09: { 'service': 0x39e1FA00, 'desc': "Calibrated VWC", 'type': 'float32', 'page': 25 },
  0x39e1FA0A: { 'service': 0x39e1FA00, 'desc': "Calibrated air temperature", 'type': 'float32', 'page': 25 },
  0x39e1FA0B: { 'service': 0x39e1FA00, 'desc': "Calibrated DLI", 'type': 'float32', 'page': 25 },
  0x39e1FA0C: { 'service': 0x39e1FA00, 'desc': "Calibrated EA", 'type': 'float32', 'page': 25 },
  0x39e1FA0D: { 'service': 0x39e1FA00, 'desc': "Calibrated ECB", 'type': 'float32', 'page': 25 },
  0x39e1FA0E: { 'service': 0x39e1FA00, 'desc': "Calibrated EC porous", 'type': 'float32', 'page': 25 },

  0x39e1FB00: { 'desc': "Upload Service", 'page': 26 },
  0x39e1FB01: { 'service': 0x39e1FB00, 'desc': "Tx buffer", 'type': 'U8*20', 'page': 26 },
  0x39e1FB02: { 'service': 0x39e1FB00, 'desc': "Tx Status", 'type': 'U8', 'page': 26 },
  0x39e1FB03: { 'service': 0x39e1FB00, 'desc': "Rx Status", 'type': 'U8', 'page': 26 },

  0x39e1FC00: { 'desc': "History Service", 'page': 26 },
  0x39e1FC01: { 'service': 0x39e1FC00, 'desc': "Nb entries", 'type': 'U16', 'page': 26 },
  0x39e1FC02: { 'service': 0x39e1FC00, 'desc': "Last entry index", 'type': 'U32', 'page': 26 },
  0x39e1FC03: { 'service': 0x39e1FC00, 'desc': "Transfer start index", 'type': 'U32', 'page': 26 },
  0x39e1FC04: { 'service': 0x39e1FC00, 'desc': "Current session ID", 'type': 'U16', 'page': 26 },
  0x39e1FC05: { 'service': 0x39e1FC00, 'desc': "Current Session start index", 'type': 'U32', 'page': 26 },
  0x39e1FC06: { 'service': 0x39e1FC00, 'desc': "Current Session period", 'type': 'U16', 'page': 26 },

  0x39e1FD00: { 'desc': "FlowerPower Clock Service", 'page': 26 },
  0x39e1FD01: { 'service': 0x39e1FD00, 'desc': "FlowerPower current time", 'type': 'U32', 'page': 26 },

  0x39e1FE00: { 'desc': "Flower Power Calibration Service", 'page': 26 },
  0x39e1FE01: { 'service': 0x39e1FE00, 'desc': "Calibration data", 'type': 'U16*11', 'page': 26 },
  0x39e1FE02: { 'service': 0x39e1FE00, 'desc': "Force bond characteristic", 'type': 'U8', 'page': 27 },
  0x39e1FE03: { 'service': 0x39e1FE00, 'desc': "Name", 'type': 'UTF8', 'page': 27 },
  0x39e1FE04: { 'service': 0x39e1FE00, 'desc': "Color", 'type': 'U16', 'page': 27 },

  0xF000FFC0: { 'desc': "Over The Air Download Service", 'page': 27 },
  0xF000FFC1: { 'service': 0xF000FFC0, 'desc': "OAD image notify", 'type': 'U8*8', 'page': 27 },
  0xF000FFC2: { 'service': 0xF000FFC0, 'desc': "OAD image block", 'type': 'U8*18', 'page': 27 },
}

decode = {
  'float32': '<f',
  'U8': '<B',
  'U16': '<H',
  'U32': '<I',
  'U16*11': '<11H'
}

def uuid_desc(uuid):
    uuid = int(uuid[:8],16)
    uuid = uuid & 0xFFFFFFFF
    if uuid in uuids.keys():
        return uuids[uuid]['desc']
    return None

def uuid_type(uuid):
    uuid = int(uuid[:8],16)
    uuid = uuid & 0xFFFFFFFF
    if uuid in uuids.keys():
        return uuids[uuid]['type']
    return None


def prop2str(prop):
    return ""

for dev in devices:
    print("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi))
    for (adtype, desc, value) in dev.getScanData():
        print("  %04x: %s = %s" % (adtype, desc, value))
    print("Try to connect to %s..." % dev.addr)
    for i in range(0,5):
        try:
            p = Peripheral(dev)
            break
        except BTLEException as e:
            print("Problems connecting to %s:" % dev.addr, e)
            continue
    if not p:
        print("Could not connect to device, giving up.")
        continue
    try:
        # p = Peripheral(dev)
        p.setDelegate( MyDelegate(None) )
        for service in p.getServices():
            uuid = str(service.uuid)
            uuid = uuid[:4] + "'''" + uuid[4:8] + "'''" # + uuid[8:] # '''
            desc = uuid_desc(str(service.uuid)[:8]) or "?"
            print("|  Service          || <code>%s</code> || || || %s || ||" % (uuid, desc))
            print("|-")
            for char in service.getCharacteristics():
                uuid = str(char.uuid)
                uuid = uuid[:4] + "'''" + uuid[4:8] + "'''"   # + uuid[8:] # '''
                desc = uuid_desc(str(char.uuid)[:8]) or "?"
                type = uuid_type(str(char.uuid)[:8]) or ""
                data = ""
                if char.supportsRead():
                    if str(service.uuid) in ignore_char:
                        data = '(ignored service)'
                    elif str(char.uuid) in ignore_char:
                        data = '(ignored characteristic)'
                    elif type == 'UTF8':
                        data = char.read()
                    elif type in decode.keys():
                        data = ','.join(map(str, struct.unpack(decode[type], char.read())))
                    else:
                        data = '0x'+str(binascii.hexlify(char.read()))
                print("|    Characteristic || <code>%s</code> || <code>%04x</code> || %s || %s || %s || %s " % (uuid, char.properties, char.propertiesToString(), type, desc, data))
                print("|-")
    except BTLEException as e:
        print("got an BTLEException: ", e)
