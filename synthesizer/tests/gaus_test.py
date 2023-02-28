import serial
import struct
import time
from scipy.signal import gaussian
import numpy as np


def gaussian_envelope(x, mu=0.0, sigma=1.0):
    x = float(x - mu) / sigma
    return np.exp(-x*x/2.0)


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

def getFTW(freqMHz):
  # 36-bit DDS
  # 1 MHz = 223696213.33333333333333333333333 FTW
  MHz = 223696213.33333333333333333333333
  return int(round(freqMHz * MHz))>>4

def main():
    dev = ka015()
    print('resetting sequencer')
    dev.reset()
    time.sleep(2)
    print('Writing to device')
    channel = 0x0F #all channels
    # channel = 0x05 #channel 0 and 2

    dt = 6.5e-9
    t_stop = 5

    N = 50  # number of time steps

    step = int(t_stop/N/dt)
    address_arr = np.arange(0, N)

    w = t_stop/4 #sec
    A = 46863
    for a in address_arr:
        f = getFTW(1)
        if a == 0:
            phase_change = True
        else:
            phase_change = False
        amp = int(A*gaussian_envelope(step*a, step*N/2, w/dt))
        print(amp)

        dev.write_timestamp(
            channel       = channel,
            address       = a,
            timestamp     = step*a,
            phase_update=phase_change,
            ptw           = 0x101,
            atw           = amp,
            ftw           = f
        )
    # dev.write_timestamp(
    #   channel       = 0x01,
    #   address       = 0x0001,
    #   timestamp     = 0x124F7FFE, #2 sec
    #   phase_update  = False,
    #   ptw           = 0x101,
    #   atw           = 0xCFFF,
    #   ftw           = 0x0FF03030
    # )
    # dev.write_timestamp(
    #   channel       = 0x04,
    #   address       = 0x0001,
    #   timestamp     = 0x124F7FFE, #2 sec
    #   phase_update  = False,
    #   ptw           = 0x901,
    #   atw           = 0xCFFF,
    #   ftw           = 0x0FF03031
    # )


    #amp set to 0
    dev.write_timestamp(
        channel=channel,
        address=N,
        timestamp=step*N,  # 4 sec
        phase_update=False,
        ptw=0x101,
        atw=0x0,
        ftw=getFTW(99.8)
    )
    #terminate
    dev.write_timestamp(
      channel       = channel,
      address=N+1,
      timestamp=step*(N+1),
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
