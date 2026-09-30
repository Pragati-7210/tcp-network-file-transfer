import socket
import struct
import hashlib
import selectors
import time
import os


HOST = "0.0.0.0"
PORT = 5000
CHUNK_SIZE = 4096


# ==================================================
# Store the state of each connected client
# ==================================================

class ClientState:

    def __init__(self, connection, address):

        self.connection = connection
        self.address = address

        # Incoming TCP data
        self.buffer = bytearray()

        # Protocol state
        self.stage = "filename_length"

        # File information
        self.filename = None
        self.filename_length = 0
        self.file_size = 0

        # Transfer information
        self.received = 0

        # Hash information
        self.expected_hash = None
        self.sha256 = hashlib.sha256()

        # File handle
        self.file = None

        # Timing
        self.start_time = None
        self.last_update = 0


# ==================================================
# Close client connection
# ==================================================

def close_connection(selector, state):

    print(f"\n[{state.address}] Connection closed")

    if state.file is not None:
        state.file.close()

    try:
        selector.unregister(state.connection)
    except Exception:
        pass

    state.connection.close()


# ==================================================
# Process data received from a client
# ==================================================

def process_data(selector, state):

    while True:

        # --------------------------------------------------
        # STAGE 1: Receive filename length
        # --------------------------------------------------

        if state.stage == "filename_length":

            if len(state.buffer) < 4:
                return

            data = bytes(state.buffer[:4])

            del state.buffer[:4]

            state.filename_length = struct.unpack(
                "!I",
                data
            )[0]

            state.stage = "filename"


        # --------------------------------------------------
        # STAGE 2: Receive filename
        # --------------------------------------------------

        elif state.stage == "filename":

            if len(state.buffer) < state.filename_length:
                return

            data = bytes(
                state.buffer[:state.filename_length]
            )

            del state.buffer[:state.filename_length]

            state.filename = os.path.basename(
                data.decode()
            )

            state.stage = "file_size"


        # --------------------------------------------------
        # STAGE 3: Receive file size
        # --------------------------------------------------

        elif state.stage == "file_size":

            if len(state.buffer) < 8:
                return

            data = bytes(state.buffer[:8])

            del state.buffer[:8]

            state.file_size = struct.unpack(
                "!Q",
                data
            )[0]

            state.stage = "hash"


        # --------------------------------------------------
        # STAGE 4: Receive SHA-256
        # --------------------------------------------------

        elif state.stage == "hash":

            if len(state.buffer) < 32:
                return

            state.expected_hash = bytes(
                state.buffer[:32]
            )

            del state.buffer[:32]

            state.file = open(
                "received_" + state.filename,
                "wb"
            )

            state.start_time = time.monotonic()
            state.last_update = state.start_time

            print(
                f"\n[{state.address}] "
                f"Receiving {state.filename} "
                f"({state.file_size / (1024 * 1024):.2f} MB)"
            )

            state.stage = "file_data"


        # --------------------------------------------------
        # STAGE 5: Receive file data
        # --------------------------------------------------

        elif state.stage == "file_data":

            if len(state.buffer) == 0:
                return

            remaining = (
                state.file_size - state.received
            )

            amount = min(
                len(state.buffer),
                remaining
            )

            data = bytes(
                state.buffer[:amount]
            )

            del state.buffer[:amount]

            state.file.write(data)

            state.sha256.update(data)

            state.received += len(data)


            # --------------------------------------------------
            # Progress display
            # --------------------------------------------------

            current_time = time.monotonic()

            if (
                current_time - state.last_update
                >= 0.2
            ):

                elapsed = (
                    current_time - state.start_time
                )

                progress = (
                    state.received
                    / state.file_size
                    * 100
                )

                speed = (
                    state.received
                    / elapsed
                    / (1024 * 1024)
                )

                print(
                    f"\r[{state.address}] "
                    f"Progress: {progress:6.2f}% | "
                    f"Received: "
                    f"{state.received / (1024 * 1024):8.2f} MB | "
                    f"Speed: {speed:8.2f} MB/s",
                    end=""
                )

                state.last_update = current_time


            # --------------------------------------------------
            # File completely received
            # --------------------------------------------------

            if state.received == state.file_size:

                elapsed = (
                    time.monotonic()
                    - state.start_time
                )

                speed = (
                    state.received
                    / elapsed
                    / (1024 * 1024)
                )

                print(
                    f"\r[{state.address}] "
                    f"Progress: 100.00% | "
                    f"Received: "
                    f"{state.received / (1024 * 1024):8.2f} MB | "
                    f"Speed: {speed:8.2f} MB/s"
                )

                state.file.close()

                state.file = None

                actual_hash = state.sha256.digest()


                print(
                    f"[{state.address}] "
                    f"File received: "
                    f"{state.received}/{state.file_size} bytes"
                )


                print(
                    f"[{state.address}] "
                    f"Expected SHA-256: "
                    f"{state.expected_hash.hex()}"
                )


                print(
                    f"[{state.address}] "
                    f"Actual SHA-256:   "
                    f"{actual_hash.hex()}"
                )


                # --------------------------------------------------
                # Send application-level ACK
                # --------------------------------------------------

                if state.expected_hash == actual_hash:

                    print(
                        f"[{state.address}] "
                        f"Integrity check: OK ✓"
                    )

                    state.connection.sendall(
                        b"OK"
                    )

                    print(
                        f"[{state.address}] "
                        f"ACK sent: OK"
                    )


                else:

                    print(
                        f"[{state.address}] "
                        f"Integrity check: FAILED ✗"
                    )

                    state.connection.sendall(
                        b"FAILED"
                    )

                    print(
                        f"[{state.address}] "
                        f"ACK sent: FAILED"
                    )


                state.stage = "complete"

                return


        # --------------------------------------------------
        # STAGE 6: Transfer complete
        # --------------------------------------------------

        elif state.stage == "complete":

            return


# ==================================================
# Accept a new client
# ==================================================

def accept_client(server_socket, selector):

    connection, address = server_socket.accept()

    print(
        f"\n[{address}] Client connected"
    )

    connection.setblocking(False)

    state = ClientState(
        connection,
        address
    )

    selector.register(
        connection,
        selectors.EVENT_READ,
        state
    )


# ==================================================
# Create server
# ==================================================

server = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)


server.setsockopt(
    socket.SOL_SOCKET,
    socket.SO_REUSEADDR,
    1
)


server.bind(
    (HOST, PORT)
)


server.listen(100)

server.setblocking(False)


# ==================================================
# Create selector
# ==================================================

selector = selectors.DefaultSelector()


selector.register(
    server,
    selectors.EVENT_READ
)


print(
    f"Selector server listening on port {PORT}..."
)


# ==================================================
# Main event loop
# ==================================================

while True:

    events = selector.select()

    for key, mask in events:

        # --------------------------------------------------
        # New client connection
        # --------------------------------------------------

        if key.fileobj is server:

            accept_client(
                server,
                selector
            )

            continue


        # --------------------------------------------------
        # Existing client has data
        # --------------------------------------------------

        state = key.data

        try:

            data = state.connection.recv(
                CHUNK_SIZE
            )


            # Client disconnected
            if not data:

                close_connection(
                    selector,
                    state
                )

                continue


            # Add incoming data to buffer
            state.buffer.extend(data)


            # Process whatever we have received
            process_data(
                selector,
                state
            )


        except Exception as error:

            print(
                f"\n[{state.address}] "
                f"Error: {error}"
            )

            close_connection(
                selector,
                state
            )
