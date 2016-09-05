from __future__ import print_function

from bluepy.btle import UUID, Scanner, DefaultDelegate, Peripheral, BTLEException
import binascii
import struct

debug = 0

class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            print("Discovered device", dev.addr)
        elif isNewData:
            print("Received new data from", dev.addr)


# scanner = Scanner().withDelegate(ScanDelegate())
# devices = scanner.scan(5.0)
ignore_char = [
  # '00002a00-0000-1000-8000-00805f9b34fb',
  '39e1fe02-84a8-11e2-afba-0002a5d5c51b'
]


def prop2str(prop):
    return ""


FP_SERVICE_LIFE = 0x39e1FA00
FP_CHAR_LIFE_DLI = 0x39e1FA01
FP_CHAR_LIFE_DLI_CAL = 0x39e1FA0B
FP_CHAR_LIFE_PERIOD = 0x39e1FA06

FP_UPLOAD = 0x39e1FB00
FP_UPLOAD_TX_BUFFER = 0x39e1FB01
FP_UPLOAD_TX_STATUS = 0x39e1FB02
FP_UPLOAD_RX_STATUS = 0x39e1FB03

FP_HISTORY = 0x39e1FC00  #: {'desc': "History Service", 'page': 26},
FP_HISTORY_NB_ENTRIES = 0x39e1FC01  #: {'service': 0x39e1FC00, 'desc': "Nb entries", 'type': 'U16', 'page': 26},
FP_HISTORY_LAST_INDEX = 0x39e1FC02  #: {'service': 0x39e1FC00, 'desc': "Last entry index", 'type': 'U32', 'page': 26},
FP_HISTORY_START_INDEX = 0x39e1FC03  #: {'service': 0x39e1FC00, 'desc': "Transfer start index", 'type': 'U32', 'page': 26},
FP_HISTORY_SESSION_ID = 0x39e1FC04  #: {'service': 0x39e1FC00, 'desc': "Current session ID", 'type': 'U16', 'page': 26},
FP_HISTORY_SESSION_START = 0x39e1FC05  #: {'service': 0x39e1FC00, 'desc': "Current Session start index", 'type': 'U32', 'page': 26},
FP_HISTORY_SESSION_PERIOD = 0x39e1FC06  #: {'service': 0x39e1FC00, 'desc': "Current Session period", 'type': 'U16', 'page': 26},


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
        return self.unpack(self.char.read())

    def write(self, data):
        return self.char.write(struct.pack(self.fmt, data))

    def getHandle(self):
        return self.char.getHandle()

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

    def get_tx_state(self, state):
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

            elif self.tx_state is 1:  #self.TX_TRANSFER:
                2 <= debug and print("TX TRANSFER")
                if not self.p.waitForNotifications(2.0):
                    print("timeout waiting for frames")
                    self.set_rx_state(self.RX_ERROR)
                    break

            elif self.tx_state is self.TX_WAIT_ACK:
                # print("TX WAIT_ACK")
                if self.frames_complete or self.frames_ready:
                    2 <= debug and print("frames_complete=%d, frames_ready=%d, send ACK" % (self.frames_complete, self.frames_ready))
                    self.c_upload_rxs.write(self.RX_ACK)
                else:
                    2 <= debug and print("frames_complete=%d, frames_ready=%d, send NACK" % (self.frames_complete, self.frames_ready))
                    self.c_upload_rxs.write(self.RX_NACK)
                continue

            else:
                print("unknown TX state %d:", self.tx_state)
                self.set_rx_state(self.RX_CANCEL)
                break

        print("upload done.")
        data = self.frames[1]
        for i in range(2, self.frames_max):
            data += self.frames[i]
        rest = self.buffer_size % 18
        print("rest is %d" % rest)
        if rest > 0:
            data += self.frames[self.frames_max][0:rest]
        else:
            data += self.frames[self.frames_max]
        print("got data of length %d" % len(data))
        return data


def save(filename, data):
    with open(filename, 'bw') as f:
        f.write(data)
    f.close()
    print("data was written to",filename)

class PlantSensor(DefaultDelegate):

    def __init__(self, p):
        DefaultDelegate.__init__(self)
        self.p = Peripheral(p)
        self.p.setDelegate(self)
        self.handles = {}
        self.s_life = self.p.getServiceByUUID(FP_UUID(FP_SERVICE_LIFE))
        self.c_dli = self.s_life.getCharacteristics(FP_UUID(FP_CHAR_LIFE_DLI))[0]
        self.c_dlic = self.s_life.getCharacteristics(FP_UUID(FP_CHAR_LIFE_DLI_CAL))[0]
        self.c_lifep = self.s_life.getCharacteristics(FP_UUID(FP_CHAR_LIFE_PERIOD))[0]

        self.subscribe(self.c_dli, self.handle_dli)
        self.subscribe(self.c_dlic, self.handle_dlic)

        self.upload = FPUpload(self.p)
        self.subscribe(self.upload.c_upload_txb, self.upload.handle_tx_buffer)
        self.subscribe(self.upload.c_upload_txs, self.upload.handle_tx_status)

        print("handle for dli : 0x%04x" % self.c_dli.getHandle())
        print("handle for dlic: 0x%04x" % self.c_dlic.getHandle())

    def set_life_period(self, secs):
        if secs > 255:
            secs = 255
        self.c_lifep.write(struct.pack('<B', secs))

    def subscribe(self, char, func):
        handle = char.getHandle()
        self.handles[handle] = func
        self.p.writeCharacteristic(handle+1, struct.pack('<H', 0x1))
        print("registered for handle 0x%04x" % handle)
        return handle

    def unsubscribe(self, handle):
        if handle in self.handles.keys():
            self.handles.pop(handle)
        self.p.writeCharacteristic(handle + 1, struct.pack('<H', 0x0))

    def handle_dli(self, data):
        #print("got data for DLI:  %d" % struct.unpack('<H', data))
        return

    def handle_dlic(self, data):
        print("got data for DLIC: %f" % struct.unpack('<f', data))

    def handleNotification(self, handle, data):
        # ... perhaps check cHandle
        # ... process 'data'
        #print("got data for handle 0x%04x" % handle)
        if handle in self.handles.keys():
            self.handles[handle](data)


def life_test(ps):
    my_count = 0
    ps.set_life_period(1)
    while True:
        my_count += 1
        if my_count > 10:
            break
        if not ps.p.waitForNotifications(2.0):
            print("Waiting...")
        # Perhaps do something else here
    ps.set_life_period(0)

# life_test(ps)
for i in range(1, 50):
    ps = PlantSensor('a0:14:3d:07:cf:d6')  #
    save('fp-cfd6-%03d.dat' % i, ps.upload.receive(count=i))
    ps.p.disconnect()
