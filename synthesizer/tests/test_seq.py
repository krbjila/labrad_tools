import socket
from time import sleep

def trigger(sock):
  tosend = bytearray.fromhex(f"A200")
  sock.sendto(tosend, dest)

def reset(sock):
  tosend = bytearray.fromhex(f"A300")
  sock.sendto(tosend, dest)

def turn_ch_on(ch, freq, sock):
  tosend = bytearray.fromhex(f"A100000000000000")
  sock.sendto(tosend, dest)
  tosend = bytearray.fromhex(f"A110000000000000")
  sock.sendto(tosend, dest)
  tosend = bytearray.fromhex(f"A1200000DFFFFFFF")
  sock.sendto(tosend, dest)
  tosend = bytearray.fromhex(f"A13000001000FFFF")
  sock.sendto(tosend, dest)
  tosend = bytearray.fromhex(f"A100000100000000")
  sock.sendto(tosend, dest)
  tosend = bytearray.fromhex(f"A110000110025800")
  sock.sendto(tosend, dest)
  tosend = bytearray.fromhex(f"A12000011FFFFFFF")
  sock.sendto(tosend, dest)
  tosend = bytearray.fromhex(f"A13000011000FFFF")
  sock.sendto(tosend, dest)
  tosend = bytearray.fromhex(f"A100000200010000")
  sock.sendto(tosend, dest)
  tosend = bytearray.fromhex(f"A110000200000000")
  sock.sendto(tosend, dest)
  tosend = bytearray.fromhex(f"A12000020FFFFFFF")
  sock.sendto(tosend, dest)
  tosend = bytearray.fromhex(f"A13000021000FFFF")
  sock.sendto(tosend, dest)
  tosend = bytearray.fromhex(f"A100000300000000")
  sock.sendto(tosend, dest)
  tosend = bytearray.fromhex(f"A110000310025800")
  sock.sendto(tosend, dest)
  tosend = bytearray.fromhex(f"A120000300FFFFFF")
  sock.sendto(tosend, dest)
  tosend = bytearray.fromhex(f"A13000031000FFFF")
  sock.sendto(tosend, dest)
  tosend = bytearray.fromhex(f"A100000400000000")
  sock.sendto(tosend, dest)
  tosend = bytearray.fromhex(f"A110000400000000")
  sock.sendto(tosend, dest)
  tosend = bytearray.fromhex(f"A120000400000000")
  sock.sendto(tosend, dest)
  tosend = bytearray.fromhex(f"A130000400000000")
  sock.sendto(tosend, dest)

timeout = 1.02
port = 804
host = '192.168.7.179'
dest = (host, int(port))
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
sock.settimeout(timeout)

reset(sock)
sleep(0.5)
turn_ch_on(0,0,sock)
# trigger(sock)