import serial
import struct
import time

class ka015:
  """Simple test class for KA015 synthesizer"""

  def __init__(self):
    self.uart = serial.Serial('COM4', 115200, timeout=0.1)

  def write_timestamp(self, channel, address, timestamp, phase_update, ptw, atw, ftw):
    print("  New timestamp")
    phase = ptw
    if(phase_update):
      phase += 0x1000 #set update bit
    self.uart.write(struct.pack('>B', 0xA1))
    print("fifo trans", struct.pack('>B', 0xA1))

    self.uart.write(struct.pack('>B', channel))
    print("channel", struct.pack('>B', channel))

    self.uart.write(struct.pack('>H', address))
    print("address", struct.pack('>H', address))

    self.uart.write(struct.pack('>I', timestamp))
    print("time", struct.pack('>I', timestamp))

    self.uart.write(struct.pack('>H', phase))
    print("phase", struct.pack('>H', phase))

    self.uart.write(struct.pack('>H', atw))
    print("atw", struct.pack('>H', atw))

    self.uart.write(struct.pack('>I', ftw))
    print("ftw", struct.pack('>I', ftw))

    self.uart.write(struct.pack('>B', 0x00))
    print("terminator", struct.pack('>B', 0x00))

    print("  End timestamp")

    #the uart buffer is only 16 bytes deep, so we need to
    #wait until all data is written after every word
    self.uart.flush()

  def trigger(self):
    msg = bytearray(2)
    msg[0] = 0xA2
    msg[1] = 0x00
    self.uart.write(msg)
    #the uart buffer is only 16 bytes deep, so we need to
    #wait until all data is written after every word
    self.uart.flush()

  def reset(self):
    msg = bytearray(2)
    msg[0] = 0xA3
    msg[1] = 0x00
    self.uart.write(msg)
    #the uart buffer is only 16 bytes deep, so we need to
    #wait until all data is written after every word
    self.uart.flush()

def main():
    dev = ka015()
    print('resetting sequencer')
    dev.reset()
    time.sleep(2)
    print('Writing to device')
    # channel = 0x0F #all channels
    channel = 0x05 #channel 0 and 2
    dev.write_timestamp(
      channel       = channel,
      address       = 0x0000,
      timestamp     = 0x00000000,
      phase_update  = True,
      ptw           = 0x101,
      atw           = 0x8FFF,
      ftw           = 0x0FF03030
    )
    dev.write_timestamp(
      channel       = 0x01,
      address       = 0x0001,
      timestamp     = 0x124F7FFE, #2 sec
      phase_update  = False,
      ptw           = 0x101,
      atw           = 0xCFFF,
      ftw           = 0x0FF03030
    )
    dev.write_timestamp(
      channel       = 0x04,
      address       = 0x0001,
      timestamp     = 0x124F7FFE, #2 sec
      phase_update  = False,
      ptw           = 0x901,
      atw           = 0xCFFF,
      ftw           = 0x0FF03031
    )
    dev.write_timestamp(
      channel       = channel,
      address       = 0x0002,
      timestamp     = 0x249EFFFC, #4 sec
      phase_update  = True,
      ptw           = 0x101,
      atw           = 0xFFFF,
      ftw           = 0x0FF03030
    )
    #terminate
    dev.write_timestamp(
      channel       = channel,
      address       = 0x0003,
      timestamp     = 0x00000000,
      phase_update  = False,
      ptw           = 0x000,
      atw           = 0x0000,
      ftw           = 0x00000000
    )

    time.sleep(1)

    print('Triggering device')
    dev.trigger()

if __name__ == '__main__':
    main()