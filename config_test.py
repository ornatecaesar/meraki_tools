import socket

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# IP and port to send to
server_address = ('209.206.56.124', 7351)

# Data to send (can be anything, e.g., a byte string)
message = b'This is a test packet'

i = 0
# Send the packet
while i < 50:
    sock.sendto(message, server_address)
    print(f"Sending packet {i}")
    i = i +1

# Close the socket
sock.close()

print("Packets sent!")