import socket
import struct
import sys

message = 'MultiCast'
multicast_group = ('224.3.29.71', 10000)

# Create the datagram socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Set a timeout so the socket does not block indefinitely when trying
# to receive data.
sock.settimeout(0.2)

# Set the time-to-live for messages to 1 so they do not go past the
# local network segment.
ttl = struct.pack('b', 1)
sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

encoded_message = str.encode(message)
send_message = sock.sendto(encoded_message, multicast_group)




while True:
        print("waiting")

        try:
            print("send Message")
            send_message = sock.sendto(encoded_message, multicast_group)
            data, server = sock.recvfrom(16)

        except socket.timeout:
            print('timed out, no more responses')
        else:
            print("Got a response")


print("closing socket")
sock.close()
