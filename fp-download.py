#!/usr/bin/python3

from __future__ import print_function

from bluepy.btle import UUID, Scanner, DefaultDelegate, Peripheral, BTLEException
import struct
import argparse
from time import time
import string

SCRIPT = 'fp-download.py v1.1'

debug = 0

'''
fp-download.py Copyright 2016 by gandy92@googlemail.com

Reads complete historic data from sensor and stores it in a text file.
Warning: If used excessively, sensor battery life may be reduced significantly!

Works with python 2.7 and 3.x, requires working bluez installation (v5.37 or above)
and a fairly recent version of bluepy (best installed w/ pip or pip3), see
https://github.com/IanHarvey/bluepy

Usage:
    python fp-download --addr BTADDR

    where BTADDR is the address of the BT-4.0 sensor device

Output file will be named 'hist-ABCD-SSID.dat' where ABCD is the short ID of the sensor
'''

FP_GAP = 0x1800
FP_DEV_NAME = 0x2A00

FP_INFO = 0x180A
FP_INFO_FW_VERSION = 0x2A26

FB_BATTERY = 0x180f
FB_BATTERY_LEVEL = 0x2A19

FP_SERVICE_LIFE = 0x39e1FA00
FP_CHAR_LIFE_DLI = 0x39e1FA01
FP_CHAR_LIFE_SEC = 0x39e1FA02
FP_CHAR_LIFE_STEMP = 0x39e1FA03
FP_CHAR_LIFE_ATEMP = 0x39e1FA04
FP_CHAR_LIFE_VWC = 0x39e1FA05
FP_CHAR_LIFE_DLI_CAL = 0x39e1FA0B
FP_CHAR_LIFE_PERIOD = 0x39e1FA06

FP_SERVICE_NEW = 0x39e1fd80
FP_CHAR_NEW_1 = 0x39e1fd81
FP_CHAR_NEW_2 = 0x39e1fd82
FP_CHAR_NEW_3 = 0x39e1fd83
FP_CHAR_NEW_4 = 0x39e1fd84
FP_CHAR_NEW_5 = 0x39e1fd85
FP_CHAR_NEW_6 = 0x39e1fd86

FP_UPLOAD = 0x39e1FB00
FP_UPLOAD_TX_BUFFER = 0x39e1FB01
FP_UPLOAD_TX_STATUS = 0x39e1FB02
FP_UPLOAD_RX_STATUS = 0x39e1FB03

FP_HISTORY = 0x39e1FC00
FP_HISTORY_NB_ENTRIES = 0x39e1FC01
FP_HISTORY_LAST_INDEX = 0x39e1FC02
FP_HISTORY_START_INDEX = 0x39e1FC03
FP_HISTORY_SESSION_ID = 0x39e1FC04
FP_HISTORY_SESSION_START = 0x39e1FC05
FP_HISTORY_SESSION_PERIOD = 0x39e1FC06

FB_CALIB = 0x39e1FE00
FB_CALIB_DATA = 0x39e1FE01

FB_CLOCK = 0x39e1FD00
FB_TIME = 0x39e1FD01


def device_is_fp(dev):
    for (adtype, desc, value) in dev.getScanData():
        if adtype == 6 and value == '1bc5d5a50200baafe211a88400fae139':
            return 1
    return 0


class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if not device_is_fp(dev):
            return
        if isNewDev:
            print("Discovered device", dev.addr)
        elif isNewData:
            print("Received new data from", dev.addr)


def FP_UUID(val):
    if isinstance(val, str):
        return UUID(val)
    elif (val & 0xffff0000) == 0x00000000:
        return UUID("%08X-0000-1000-8000-00805f9b34fb" % (val & 0xffffffff))
    elif (val & 0xffff0000) == 0xf0000000:
        return UUID("%08X-0451-4000-b000-000000000000" % (val & 0xffffffff))
    elif (val & 0xffff0000) == 0x39e10000:
        return UUID("%08X-84a8-11e2-afba-0002a5d5c51b" % (val & 0xffffffff))


class FPRegister:

    def __init__(self, service, uuid, fmt):
        self.service = service
        self.uuid = uuid
        self.fmt = fmt
        self.char = self.service.getCharacteristics(uuid)[0]

    def unpack(self, data):
        return struct.unpack(self.fmt, data)[0]

    def read(self):
        if self.fmt == 'utf8':
            return str(self.char.read())
        return self.unpack(self.char.read())

    def str(self):
        if self.fmt == 'utf8':
            return str(self.char.read())
        return ','.join(map(str, struct.unpack(self.fmt, self.char.read())))

    def write(self, data):
        return self.char.write(struct.pack(self.fmt, data))

    def getHandle(self):
        return self.char.getHandle()


def clean_str(str):
    return ''.join(filter(lambda x: x in string.printable, str))


CT_UTF8 = 'utf8'
CT_U8 = '<B'
CT_U16 = '<H'
CT_U32 = '<L'
CT_F32 = '<f'


class FPUpload:
    RX_STANDBY = 0
    RX_RECEIVING = 1
    RX_ACK = 2
    RX_NACK = 3
    RX_CANCEL = 4
    RX_ERROR = 5

    TX_IDLE = 0
    TX_TRANSFER = 1
    TX_WAIT_ACK = 2

    def __init__(self, plant):
        self.p = plant
        self.rx_state = self.RX_STANDBY
        self.tx_state = self.TX_IDLE

        self.s_upload = self.p.getServiceByUUID(FP_UUID(FP_UPLOAD))
        self.c_upload_txb = self.s_upload.getCharacteristics(FP_UUID(FP_UPLOAD_TX_BUFFER))[0]
        self.c_upload_txs = FPRegister(self.s_upload, FP_UUID(FP_UPLOAD_TX_STATUS), CT_U8)
        self.c_upload_rxs = FPRegister(self.s_upload, FP_UUID(FP_UPLOAD_RX_STATUS), CT_U8)

        self.s_hist = self.p.getServiceByUUID(FP_UUID(FP_HISTORY))
        self.c_hist_nb_entries = FPRegister(self.s_hist, FP_UUID(FP_HISTORY_NB_ENTRIES), CT_U16)
        self.c_hist_last_index = FPRegister(self.s_hist, FP_UUID(FP_HISTORY_LAST_INDEX), CT_U32)
        self.c_hist_start_index = FPRegister(self.s_hist, FP_UUID(FP_HISTORY_START_INDEX), CT_U32)
        self.c_hist_session_id = FPRegister(self.s_hist, FP_UUID(FP_HISTORY_SESSION_ID), CT_U16)
        self.c_hist_session_start = FPRegister(self.s_hist, FP_UUID(FP_HISTORY_SESSION_START), CT_U32)
        self.c_hist_session_period = FPRegister(self.s_hist, FP_UUID(FP_HISTORY_SESSION_PERIOD), CT_U16)

        self.frames = {}
        self.frames_ready = 0
        self.frames_complete = 0
        self.frames_max = 0
        self.buffer_size = 0
        self.frame_set = 0

        self.data = b""
        self.records = 0
        self.last_ts = 0
        self.last_idx = 0
        self.session = 0
        self.period = 0

    def handle_tx_buffer(self, data):
        data_str = ' %02x'*18 % struct.unpack('<18B', data[2:20])
        2 <= debug and print("got new tx data frame #%04x: %s" % (struct.unpack('<H', data[0:2])[0], data_str))
        frame = struct.unpack('<H', data[0:2])[0]
        if frame == 0:
            self.buffer_size = struct.unpack('<L', data[2:6])[0]
            self.frames_max = int((self.buffer_size+17) / 18)
            print("will download %d bytes in %d frames" % (self.buffer_size, self.frames_max))

        self.frames[frame] = data[2:20]
        self.frame_set = frame >> 7
        frames_ready = 1
        for i in range(0, 128):
            num = (frame & 0xFF80) | i
            if num not in self.frames.keys():
                2 <= debug and print("> missing frame %04x" % ((frame & 0xFF80) | i))
                2 <= debug and print("> already got", self.frames.keys())
                frames_ready = 0
                break
            elif num == self.frames_max:
                2 <= debug and print("maximum frame #%04x detected" % num)
                self.frames_complete = 1
                break

        self.frames_ready = frames_ready

        return

    def handle_tx_status(self, data):
        state = struct.unpack('<B', data)[0]
        2 <= debug and print("got new tx status %d" % state)
        self.tx_state = state
        return

    def set_rx_state(self, state):
        self.rx_state = state
        self.c_upload_rxs.write(state)

    def get_tx_state(self):
        return self.c_upload_txs.read()

    def receive(self, index=None, count=None):
        print("receive new data...")
        self.set_rx_state(self.RX_STANDBY)
        self.frames = {}
        self.frames_ready = 0
        self.buffer_size = 0
        self.frame_set = 0
        self.frames_complete = 0

        if index is not None:
            self.c_hist_start_index.write(index)
        elif count is not None:
            entries = self.c_hist_nb_entries.read()
            last = self.c_hist_last_index.read()
            print("entries:", entries)
            print("last:", last)
            # first entry in history seems to be entirely different
            if count > entries:
                count = entries
            if count < 1:
                count = 1
            first = last-count+1
            print("first:", first)
            self.c_hist_start_index.write(first)

        self.set_rx_state(self.RX_RECEIVING)
        while True:
            if self.tx_state is self.TX_IDLE:
                2 <= debug and print("TX IDLE")
                if self.frames_complete:
                    print("all done, entering standby")
                    self.set_rx_state(self.RX_STANDBY)
                    break
                if not self.p.waitForNotifications(5.0):
                    print("timeout waiting for status change")
                    self.set_rx_state(self.RX_ERROR)
                    break

            elif self.tx_state is self.TX_TRANSFER:
                2 <= debug and print("TX TRANSFER")
                if not self.p.waitForNotifications(2.0):
                    print("timeout waiting for frames")
                    self.set_rx_state(self.RX_ERROR)
                    break

            elif self.tx_state is self.TX_WAIT_ACK:
                3 <= debug and print("TX WAIT_ACK")
                if self.frames_complete or self.frames_ready:
                    2 <= debug and print("frames_complete=%d, frames_ready=%d, send ACK" %
                                         (self.frames_complete, self.frames_ready))
                    self.c_upload_rxs.write(self.RX_ACK)
                else:
                    2 <= debug and print("frames_complete=%d, frames_ready=%d, send NACK" %
                                         (self.frames_complete, self.frames_ready))
                    self.c_upload_rxs.write(self.RX_NACK)
                continue

            else:
                print("unknown TX state %d:", self.tx_state)
                self.set_rx_state(self.RX_CANCEL)
                break

        print("upload done.")
        self.data = []
        if len(self.frames) < 2:
            return self
        self.data = self.frames[1]
        for i in range(2, self.frames_max):
            self.data += self.frames[i]
        rest = self.buffer_size % 18
        print("rest is %d" % rest)
        if rest > 0:
            self.data += self.frames[self.frames_max][0:rest]
        else:
            self.data += self.frames[self.frames_max]
        print("got data of length %d" % len(self.data))
        d1, d2, self.records, self.last_ts, self.last_idx, self.session, self.period = \
            struct.unpack(">BBHLLHH", self.data[0:16])

        return self

    def raw(self):
        return self.data

    def str(self):
        s = "# %d,%d,records=%d,lts=%d,lidx=%d,sid=%d,sp=%d\n" % struct.unpack(">BBHLLHH", self.data[0:16])
        s += "#\n"
        n = int((len(self.data) - 16) / 12)
        for i in range(0, n):
            s += "%d " % i
            s += (" 0x%02x%02x" * 6) % struct.unpack(">12B", self.data[16+12*i:28+12*i])
            s += (" %d" * 6) % struct.unpack(">6H", self.data[16+12*i:28+12*i])
            s += "\n"
        return s


def save(filename, data):
    with open(filename, 'w') as f:
        f.write(data)
    f.close()
    print("data was written to", filename)


class PlantSensor(DefaultDelegate):

    def __init__(self, p):
        DefaultDelegate.__init__(self)
        self.p = Peripheral(p)
        self.p.setDelegate(self)
        self.handles = {}

        self.s_gap = self.p.getServiceByUUID(FP_UUID(FP_GAP))
        self.c_name = FPRegister(self.s_gap, FP_UUID(FP_DEV_NAME), CT_UTF8)

        self.s_info = self.p.getServiceByUUID(FP_UUID(FP_INFO))
        self.c_fw_ver = FPRegister(self.s_info, FP_UUID(FP_INFO_FW_VERSION), CT_UTF8)

        self.s_calib = self.p.getServiceByUUID(FP_UUID(FB_CALIB))
        self.c_calib_data = FPRegister(self.s_calib, FP_UUID(FB_CALIB_DATA), '<11H')

        self.s_bat = self.p.getServiceByUUID(FP_UUID(FB_BATTERY))
        self.r_bat = FPRegister(self.s_bat, FP_UUID(FB_BATTERY_LEVEL), CT_U8)

        self.s_clock = self.p.getServiceByUUID(FP_UUID(FB_CLOCK))
        self.c_time = FPRegister(self.s_clock, FP_UUID(FB_TIME), CT_U32)

        self.s_life = self.p.getServiceByUUID(FP_UUID(FP_SERVICE_LIFE))
        self.c_dli = self.s_life.getCharacteristics(FP_UUID(FP_CHAR_LIFE_DLI))[0]
        self.c_dlic = self.s_life.getCharacteristics(FP_UUID(FP_CHAR_LIFE_DLI_CAL))[0]
        self.c_lifep = self.s_life.getCharacteristics(FP_UUID(FP_CHAR_LIFE_PERIOD))[0]

        self.r_dli = FPRegister(self.s_life, FP_UUID(FP_CHAR_LIFE_DLI), CT_U16)
        self.r_soil_ec = FPRegister(self.s_life, FP_UUID(FP_CHAR_LIFE_SEC), CT_U16)
        self.r_soil_temp = FPRegister(self.s_life, FP_UUID(FP_CHAR_LIFE_STEMP), CT_U16)
        self.r_air_temp = FPRegister(self.s_life, FP_UUID(FP_CHAR_LIFE_ATEMP), CT_U16)
        self.r_soil_vwc = FPRegister(self.s_life, FP_UUID(FP_CHAR_LIFE_VWC), CT_U16)
        self.r_dlic = FPRegister(self.s_life, FP_UUID(FP_CHAR_LIFE_DLI_CAL), CT_F32)

        self.upload = FPUpload(self.p)
        self.subscribe(self.upload.c_upload_txb, self.upload.handle_tx_buffer)
        self.subscribe(self.upload.c_upload_txs, self.upload.handle_tx_status)

        2 <= debug and print("handle for dli : 0x%04x" % self.c_dli.getHandle())
        2 <= debug and print("handle for dlic: 0x%04x" % self.c_dlic.getHandle())

        self.s_new = None
        self.r_new_1 = None
        self.r_new_2 = None
        self.r_new_3 = None
        self.r_new_4 = None
        self.r_new_5 = None
        self.r_new_6 = None

    def init_fw_202_regs(self):
        self.s_new = self.p.getServiceByUUID(FP_UUID(FP_SERVICE_NEW))
        self.r_new_1 = FPRegister(self.s_new, FP_UUID(FP_CHAR_NEW_1), CT_U16)
        self.r_new_2 = FPRegister(self.s_new, FP_UUID(FP_CHAR_NEW_2), CT_U16)
        self.r_new_3 = FPRegister(self.s_new, FP_UUID(FP_CHAR_NEW_3), CT_U16)
        self.r_new_4 = FPRegister(self.s_new, FP_UUID(FP_CHAR_NEW_4), CT_U16)
        self.r_new_5 = FPRegister(self.s_new, FP_UUID(FP_CHAR_NEW_5), CT_U16)
        self.r_new_6 = FPRegister(self.s_new, FP_UUID(FP_CHAR_NEW_6), CT_U8)

    def set_life_period(self, secs):
        if secs > 0:
            self.unsubscribe(self.c_dli)
            self.unsubscribe(self.c_dlic)
        else:
            self.subscribe(self.c_dli, self.handle_dli)
            self.subscribe(self.c_dlic, self.handle_dlic)
        if secs > 255:
            secs = 255
        self.c_lifep.write(struct.pack('<B', secs))

    def subscribe(self, char, func):
        handle = char.getHandle()
        self.handles[handle] = func
        self.p.writeCharacteristic(handle+1, struct.pack('<H', 0x1))
        1 <= debug and print("registered for handle 0x%04x" % handle)
        return handle

    def unsubscribe(self, handle):
        if handle in self.handles.keys():
            self.handles.pop(handle)
        self.p.writeCharacteristic(handle + 1, struct.pack('<H', 0x0))

    def handle_dli(self, data):
        2 <= debug and print("got data for DLI:  %d" % struct.unpack('<H', data))

    def handle_dlic(self, data):
        2 <= debug and print("got data for DLIC: %f" % struct.unpack('<f', data))

    def handleNotification(self, handle, data):
        # ... perhaps check cHandle
        # ... process 'data'
        # print("got data for handle 0x%04x" % handle)
        if handle in self.handles.keys():
            self.handles[handle](data)


def life_test(p):
    my_count = 0
    p.set_life_period(1)
    while True:
        my_count += 1
        if my_count > 10:
            break
        if not p.p.waitForNotifications(2.0):
            print("Waiting...")
        # Perhaps do something else here
    p.set_life_period(0)


def process_sensor(device, address):
    ps = None

    print("Try to connect to %s..." % address)
    for i in range(0, 10):
        try:
            ps = PlantSensor(device)
            break
        except BTLEException:
            print("Problems connecting to %s." % address)
            continue
    if not ps:
        print("Could not connect to device, bailing out.")
        return

    if args.light:
        print("%s: dli,dlic: %d %f" % (address, ps.r_dli.read(), ps.r_dlic.read()))

    if args.battery:
        print("%s: battery: %d" % (address, ps.r_bat.read()))

    if args.dump:
        print("%s: raw soil ec: %d" % (address, ps.r_soil_ec.read()))
        print("%s: raw soil temp: %d" % (address, ps.r_soil_temp.read()))
        print("%s: raw air temp: %d" % (address, ps.r_air_temp.read()))
        print("%s: raw soil vwc: %d" % (address, ps.r_soil_vwc.read()))

    if args.newregs:
        ps.init_fw_202_regs()
        print("%s: new reg 1: %d" % (address, ps.r_new_1.read()))
        print("%s: new reg 2: %d" % (address, ps.r_new_2.read()))
        print("%s: new reg 3: %d" % (address, ps.r_new_3.read()))
        print("%s: new reg 4: %d" % (address, ps.r_new_4.read()))
        print("%s: new reg 5: %d" % (address, ps.r_new_5.read()))
        print("%s: new reg 6: %d" % (address, ps.r_new_6.read()))

    if args.life:
        life_test(ps)

    if args.download:
        short = ps.c_name.str().split(" ")[2][0:4]
        head = '# History data collected by %s\n' % SCRIPT
        head += '# current time: %d\n' % int(time())
        head += '# sensor time: %d\n' % ps.c_time.read()
        head += '# sensor addr: %s\n' % address
        head += '# calib: %s\n' % ps.c_calib_data.str()
        head += '# firmware: %s\n' % clean_str(ps.c_fw_ver.str())
        head += '#\n'
        try:
            data = ps.upload.receive(count=10000).str()
            save('hist-%s-%03d.dat' % (short, ps.upload.session), head+data)
        except BTLEException:
            print("Problems connecting to %s." % address)

    ps.p.disconnect()


parser = argparse.ArgumentParser(prog='fp-download', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--addr',
                    #required=True,
                    help='sensor MAC-address')
parser.add_argument('--scan', action='store_const', const=1, default=0,
                    help='query all available sensors')
parser.add_argument('--download', action='store_const', const=1, default=0,
                    help='download history data')
parser.add_argument('--light', action='store_const', const=1, default=0,
                    help='print life light sensor values (raw and calibrated)')
parser.add_argument('--dump', action='store_const', const=1, default=0,
                    help='print life sensor raw values')
parser.add_argument('--battery', action='store_const', const=1, default=0,
                    help='print battery level')
parser.add_argument('--newregs', action='store_const', const=1, default=0,
                    help='print values of registers introduced with fw 2.0.2')
parser.add_argument('--life', action='store_const', const=1, default=0,
                    help='')
args = parser.parse_args()

if not args.addr and not args.scan:
    print("Error: specify sensor addr or use option --scan")
    exit(-1)

if args.addr:
    if args.scan:
        print("Error: Can not use --addr with --scan")
        exit(-1)
    process_sensor(args.addr, args.addr)

elif args.scan:
    scanner = Scanner().withDelegate(ScanDelegate())
    devices = []
    try:
        devices = scanner.scan(15.0)
    except BTLEException as e:
        print("Problems during scan:", e)

    for dev in devices:
        try:
            if device_is_fp(dev):
                print("Device %s (%s), RSSI=%d dB" % (dev.addr, dev.addrType, dev.rssi))
                process_sensor(dev, dev.addr)
        except BTLEException as e:
            print("Problems while handling %s:" % dev.addr, e)


