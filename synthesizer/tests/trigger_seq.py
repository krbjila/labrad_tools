import socket

def trigger(sock):
  tosend = bytearray.fromhex(f"A200")
  sock.sendto(tosend, dest)

timeout = 1.02
port = 804
host = '192.168.7.179'
dest = (host, int(port))
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
sock.settimeout(timeout)

trigger(sock)