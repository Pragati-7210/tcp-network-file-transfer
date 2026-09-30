import socket
import os
import struct
import sys
import hashlib
import time


HOST = "127.0.0.1"
PORT = 5000


# ==================================================
# Check command-line argument
# ==================================================

if len(sys.argv) != 2:

    print(
        "Usage: python3 client.py <filename>"
    )

    sys.exit(1)


filename = sys.argv[1]


# ==================================================
# Check that file exists
# ==================================================

if not os.path.exists(filename):

    print(
        f"File not found: {filename}"
    )

    sys.exit(1)


# ==================================================
# Create TCP socket
# ==================================================

client = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)


# ==================================================
# Connect to server
# ==================================================

client.connect(
    (HOST, PORT)
)


# ==================================================
# Get file information
# ==================================================

filename_bytes = os.path.basename(
    filename
).encode()


file_size = os.path.getsize(
    filename
)


# ==================================================
# Calculate SHA-256
# ==================================================

sha256 = hashlib.sha256()


with open(filename, "rb") as file:

    while True:

        data = file.read(4096)

        if not data:
            break

        sha256.update(data)


file_hash = sha256.digest()


# ==================================================
# Send protocol information
# ==================================================

# Send filename length
client.sendall(
    struct.pack(
        "!I",
        len(filename_bytes)
    )
)


# Send filename
client.sendall(
    filename_bytes
)


# Send file size
client.sendall(
    struct.pack(
        "!Q",
        file_size
    )
)


# Send SHA-256
client.sendall(
    file_hash
)


# ==================================================
# Send file
# ==================================================

print(
    f"Sending: {filename}"
)


print(
    f"File size: "
    f"{file_size / (1024 * 1024):.2f} MB"
)


sent = 0

start_time = time.monotonic()

last_update = start_time


with open(filename, "rb") as file:

    while True:

        data = file.read(4096)

        if not data:
            break


        client.sendall(
            data
        )


        sent += len(data)


        current_time = time.monotonic()


        # Update progress every 0.2 seconds
        if (
            current_time - last_update
            >= 0.2
        ):

            elapsed = (
                current_time
                - start_time
            )


            progress = (
                sent
                / file_size
                * 100
            )


            speed = (
                sent
                / elapsed
                / (1024 * 1024)
            )


            print(
                f"\rProgress: {progress:6.2f}% | "
                f"Sent: {sent / (1024 * 1024):8.2f} MB | "
                f"Speed: {speed:8.2f} MB/s",
                end=""
            )


            last_update = current_time


# ==================================================
# Final transfer statistics
# ==================================================

elapsed = (
    time.monotonic()
    - start_time
)


speed = (
    sent
    / elapsed
    / (1024 * 1024)
)


print(
    f"\rProgress: 100.00% | "
    f"Sent: {sent / (1024 * 1024):8.2f} MB | "
    f"Speed: {speed:8.2f} MB/s"
)


print(
    f"File sent: "
    f"{filename} ({file_size} bytes)"
)


print(
    f"SHA-256: "
    f"{sha256.hexdigest()}"
)


# ==================================================
# Wait for server ACK
# ==================================================

print(
    "Waiting for server verification..."
)


response = client.recv(
    1024
).decode()


# ==================================================
# Process server response
# ==================================================

if response == "OK":

    print(
        "Server verification: OK ✓"
    )


elif response == "FAILED":

    print(
        "Server verification: FAILED ✗"
    )


else:

    print(
        f"Unexpected server response: "
        f"{response}"
    )


# ==================================================
# Close connection
# ==================================================

client.close()