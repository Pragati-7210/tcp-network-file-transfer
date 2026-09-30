# TCP Network File Transfer System

A TCP-based client-server file transfer system built from scratch in Python using the standard socket library.

The project demonstrates practical computer networking concepts including **TCP socket programming, application-layer protocol design, message framing, chunked file transfer, non-blocking I/O, I/O multiplexing with selectors, protocol state machines, SHA-256 integrity verification, and application-level acknowledgments.**

---

## Features

- TCP client-server communication
- IPv4 socket programming
- Custom application-layer protocol
- TCP stream framing
- Chunked file transfer
- Non-blocking sockets
- I/O multiplexing using Python `selectors`
- Event-driven server architecture
- Multiple client connections
- Per-client connection state
- Protocol state machine
- Receive buffering
- SHA-256 file integrity verification
- Application-level `OK` / `FAILED` acknowledgment
- Transfer progress monitoring
- Transfer speed measurement

---

## System Architecture

```text
                     TCP CONNECTION

CLIENT                                           SERVER
  |                                                |
  |---------- TCP connection --------------------->|
  |                                                |
  |---------- Filename length -------------------->|
  |---------- Filename --------------------------->|
  |---------- File size -------------------------->|
  |---------- SHA-256 ---------------------------->|
  |---------- File data -------------------------->|
  |                                                |
  |                                      Selector Event Loop
  |                                                |
  |                                      ClientState + Buffer
  |                                                |
  |                                      Protocol State Machine
  |                                                |
  |                                      Reconstruct File
  |                                                |
  |                                      Calculate SHA-256
  |                                                |
  |                                      Compare Hashes
  |                                                |
  |<------------- OK / FAILED ---------------------|
```

---

## How It Works

The project consists of two main programs:

### `client.py`

The client:

1. Opens the selected file.
2. Calculates its SHA-256 digest.
3. Connects to the TCP server.
4. Sends the filename length.
5. Sends the filename.
6. Sends the file size.
7. Sends the SHA-256 digest.
8. Sends the file in chunks.
9. Waits for server verification.
10. Displays whether the transfer passed integrity verification.

### `server.py`

The server:

1. Creates a TCP socket.
2. Binds to port `5000`.
3. Listens for clients.
4. Uses `selectors` to monitor connections.
5. Accepts incoming clients.
6. Maintains independent state for every client.
7. Parses the application protocol.
8. Receives the file incrementally.
9. Calculates SHA-256 while receiving.
10. Compares the received hash with the expected hash.
11. Sends `OK` or `FAILED` to the client.

---

# Application-Layer Protocol

TCP provides a byte stream and does not preserve application message boundaries.

Therefore, this project defines its own framing protocol.

```text
+---------------------------+
| Filename Length           | 4 bytes
+---------------------------+
| Filename                  | Variable
+---------------------------+
| File Size                 | 8 bytes
+---------------------------+
| SHA-256 Digest            | 32 bytes
+---------------------------+
| File Data                 | Variable
+---------------------------+
```

The fields are transmitted in this exact order.

---

## Why Message Framing Is Necessary

TCP is a **byte-stream protocol**.

Suppose an application sends:

```text
HELLO
WORLD
```

TCP does not guarantee that two `recv()` calls will return exactly those two messages.

The receiver could observe data as:

```text
HELLOWORLD
```

or:

```text
HEL
LOWOR
LD
```

TCP guarantees byte ordering, not application message boundaries.

For this reason, the project sends metadata such as filename length and file size so that the server can correctly interpret the stream.

---

# TCP

TCP stands for **Transmission Control Protocol**.

The project creates TCP sockets using:

```python
socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)
```

`AF_INET` specifies IPv4.

`SOCK_STREAM` specifies a TCP stream socket.

TCP provides:

- Reliable delivery
- Ordered byte-stream delivery
- Retransmission of lost data
- Flow control
- Congestion control
- Connection-oriented communication

---

## TCP Socket Lifecycle

### Server

```text
socket()
   |
   v
bind()
   |
   v
listen()
   |
   v
accept()
   |
   v
recv()
   |
   v
close()
```

### Client

```text
socket()
   |
   v
connect()
   |
   v
sendall()
   |
   v
recv()
   |
   v
close()
```

---

# IP Address and Port

During local testing, the client uses:

```python
HOST = "127.0.0.1"
PORT = 5000
```

`127.0.0.1` is the IPv4 loopback address.

It means the client connects to a server running on the same computer.

The server uses:

```python
HOST = "0.0.0.0"
PORT = 5000
```

`0.0.0.0` allows the server to listen on available local network interfaces.

The port identifies the application endpoint.

Conceptually:

```text
IP Address
    |
    +---- identifies the machine/interface

Port
    |
    +---- identifies the service/application endpoint
```

---

# Binary Serialization

The project uses Python's `struct` module to convert integers into fixed-size binary representations.

For example:

```python
struct.pack("!I", value)
```

and:

```python
struct.unpack("!I", data)
```

The protocol uses:

```text
I = 4-byte unsigned integer

Q = 8-byte unsigned integer
```

The `!` specifies network byte order.

This allows the client and server to interpret binary metadata consistently.

---

# Chunked File Transfer

Files are not loaded entirely into memory.

Instead, they are transferred in chunks:

```python
file.read(4096)
```

and received using:

```python
connection.recv(4096)
```

Conceptually:

```text
Large File
    |
    +---- 4096 bytes
    |
    +---- 4096 bytes
    |
    +---- 4096 bytes
    |
    +---- ...
```

This allows large files to be transferred while keeping memory usage limited.

---

# SHA-256 Integrity Verification

SHA-256 is a cryptographic hash function that produces a **256-bit (32-byte) digest**.

The project uses SHA-256 for file integrity verification.

It is **not used for encryption**.

### Client

```text
Original File
     |
     v
   SHA-256
     |
     v
Expected Hash
```

The expected hash is sent to the server.

### Server

```text
Received File
     |
     v
   SHA-256
     |
     v
Actual Hash
```

The server compares:

```text
Expected Hash
      |
      | compare
      v
Actual Hash
```

If both values match:

```text
Integrity check: OK
```

Otherwise:

```text
Integrity check: FAILED
```

---

## TCP vs SHA-256

TCP and SHA-256 serve different purposes.

```text
TCP
 |
 +-- Reliable byte transport
 +-- Ordering
 +-- Retransmission
 +-- Flow control
 +-- Congestion control


SHA-256
 |
 +-- Application-level integrity verification
```

TCP handles reliable transport.

SHA-256 allows the application to verify that the reconstructed file corresponds to the supplied digest.

---

# Non-Blocking I/O

The server configures accepted client sockets using:

```python
connection.setblocking(False)
```

This prevents a client socket from indefinitely blocking the server while waiting for data.

Instead, the server monitors socket readiness through a selector.

---

# I/O Multiplexing with Selectors

The server uses:

```python
selectors.DefaultSelector()
```

A selector can monitor multiple socket connections.

Conceptually:

```text
                  Selector
                     |
          +----------+----------+
          |          |          |
          v          v          v
       Client A   Client B   Client C
          |          |          |
       Ready?      Ready?      Ready?
```

The main event loop is conceptually:

```python
while True:

    events = selector.select()

    for key, mask in events:
        # Process the socket that is ready
        pass
```

This technique is called **I/O multiplexing**.

---

# Event-Driven Server

Instead of creating a permanently blocking receive loop for every client, the server uses an event loop.

```text
                 EVENT LOOP
                     |
       +-------------+-------------+
       |             |             |
       v             v             v
    Client A      Client B      Client C
```

When a socket becomes ready, the selector reports it to the event loop.

The server then processes that connection.

---

# Per-Client State

Each connected client receives its own `ClientState`.

It stores information including:

```text
connection
address
buffer
stage
filename
filename length
file size
received bytes
expected SHA-256
running SHA-256
file handle
start time
```

Conceptually:

```text
Client A
   |
   v
ClientState A


Client B
   |
   v
ClientState B


Client C
   |
   v
ClientState C
```

This allows multiple clients to be at different stages of the protocol.

---

# Protocol State Machine

The server parses each connection using a state machine.

```text
filename_length
       |
       v
filename
       |
       v
file_size
       |
       v
hash
       |
       v
file_data
       |
       v
complete
```

For example, one client may currently be sending its filename while another client is already sending file data.

The server stores the current stage independently for each client.

---

# Receive Buffer

Every client has a byte buffer:

```python
self.buffer = bytearray()
```

Incoming TCP data is appended to this buffer.

```text
Network
   |
   v
recv()
   |
   v
Buffer
   |
   v
Enough bytes available?
   |
 +---+---+
 |       |
Yes      No
 |       |
 v       v
Parse    Wait for more data
```

This is important because one `recv()` call is not guaranteed to contain a complete application-level field.

---

# Application-Level Acknowledgment

After the complete file has been received and verified, the server sends:

```text
OK
```

or:

```text
FAILED
```

The client waits for this response:

```text
Waiting for server verification...
Server verification: OK
```

This is an **application-level acknowledgment**.

It is different from TCP's internal ACK mechanism.

TCP ACKs are used internally by TCP for reliable transport.

The application's `OK` response means:

> The complete file was received and passed the application's SHA-256 verification.

---

# Transfer Progress and Throughput

The program tracks how many bytes have been transferred.

Progress is calculated approximately as:

```text
Progress =
Transferred Bytes / Total Bytes × 100
```

Throughput is calculated as:

```text
Speed =
Transferred Bytes / Elapsed Time
```

The output can look like:

```text
Progress: 100.00%
Sent: 100.00 MB
Speed: XX.XX MB/s
```

---

# Complete Data Flow

```text
                    CLIENT
                       |
                       v
                  Select File
                       |
                       v
                Calculate SHA-256
                       |
                       v
               Connect to Server
                       |
                       v
            Send Filename Length
                       |
                       v
                Send Filename
                       |
                       v
                Send File Size
                       |
                       v
                Send SHA-256
                       |
                       v
              Send File Chunks
                       |
                       v
                     TCP
                       |
                       v
                    SERVER
                       |
                       v
               Selector Event
                       |
                       v
                 ClientState
                       |
                       v
                    Buffer
                       |
                       v
               Protocol Parser
                       |
                       v
                Receive Chunks
                       |
                       v
                  Write File
                       |
                       v
              Calculate SHA-256
                       |
                       v
                Compare Hashes
                       |
                +------+------+
                |             |
              MATCH        MISMATCH
                |             |
                v             v
               OK           FAILED
                |             |
                +------+------+
                       |
                       v
               Send Response
                       |
                       v
                    CLIENT
```

---

# Project Structure

```text
tcp-network-file-transfer/
│
├── client.py
├── server.py
├── README.md
├── .gitignore
├── test.txt
└── second.txt
```

Generated received files and large binary test files are excluded using `.gitignore`.

---

# Requirements

- Python 3
- Linux, macOS, or another environment supporting Python sockets

No external Python packages are required.

The project uses Python standard-library modules including:

```text
socket
struct
hashlib
selectors
time
os
sys
```

---

# Running the Project

## 1. Clone the Repository

Using SSH:

```bash
git clone git@github.com:Pragati-7210/tcp-network-file-transfer.git
```

Enter the project directory:

```bash
cd tcp-network-file-transfer
```

---

## 2. Start the Server

Open the first terminal:

```bash
python3 server.py
```

Expected output:

```text
Selector server listening on port 5000...
```

Leave this terminal running.

---

## 3. Start the Client

Open another terminal.

Run:

```bash
python3 client.py test.txt
```

Another example:

```bash
python3 client.py second.txt
```

---

# Example Client Output

```text
Sending: large.bin

File size: 100.00 MB

Progress: 100.00%
Sent: 100.00 MB

File sent: large.bin

SHA-256: ...

Waiting for server verification...

Server verification: OK
```

---

# Example Server Output

```text
Selector server listening on port 5000...

Client connected

Receiving large.bin

Progress: 100.00%

File received: 104857600/104857600 bytes

Expected SHA-256: ...

Actual SHA-256: ...

Integrity check: OK

ACK sent: OK
```

---

# Testing

The project was tested using:

- Small text files
- Multiple files
- A 100 MiB binary test file
- SHA-256 verification
- Application-level acknowledgments
- Selector-based client handling
- Progress measurement
- Throughput measurement

A 100 MiB test transfer successfully completed with:

```text
104857600/104857600 bytes
```

and matching expected and actual SHA-256 values.

---

# Networking Concepts Covered

This project demonstrates:

- Client-server architecture
- IPv4 addressing
- TCP ports
- Socket programming
- TCP connections
- TCP byte streams
- Application-layer protocols
- Message framing
- Binary serialization
- Network byte order
- Chunked data transfer
- Streaming file I/O
- Non-blocking sockets
- I/O multiplexing
- Selectors
- Event-driven programming
- Protocol state machines
- Per-connection state
- Receive buffers
- SHA-256 hashing
- File integrity verification
- Application-level acknowledgments
- Transfer progress measurement
- Throughput measurement

---

# Security Considerations

This project is designed primarily for learning networking concepts.

SHA-256 provides integrity verification but does **not** provide:

- Encryption
- Authentication
- Confidentiality
- Authorization

For a real production file-transfer system, secure transport such as TLS and an authentication mechanism would be necessary.

---

# Current Limitations

- No encryption
- No authentication
- No resumable transfers
- No transfer cancellation
- Primarily tested on localhost
- Simple custom protocol
- No UDP implementation
- No application-level retransmission mechanism

---

# Future Improvements

Possible extensions include:

### Reliable UDP File Transfer

Implement a UDP version with:

```text
Sequence Numbers
       |
       v
Acknowledgments
       |
       v
Timeouts
       |
       v
Retransmissions
       |
       v
Duplicate Detection
       |
       v
Packet Reordering
```

This would demonstrate several reliability mechanisms that TCP normally provides automatically.

Other possible improvements:

- TCP vs UDP performance experiments
- Wireshark packet analysis
- Network latency/loss testing
- Resumable file transfers
- Authentication
- TLS encryption
- Transfer cancellation
- Improved error protocol
- Multiple simultaneous file transfers

---

# What I Learned

This project provided practical experience with:

- How TCP client-server applications communicate
- How sockets work
- Why TCP requires application-level framing
- How binary protocol fields can be encoded
- How files can be streamed without loading them entirely into memory
- How non-blocking sockets differ from blocking sockets
- How selectors perform I/O multiplexing
- How event-driven servers maintain connection state
- How protocol state machines parse streaming data
- How SHA-256 can verify file integrity
- The difference between TCP ACKs and application-level acknowledgments

---

# Conclusion

This project implements a file-transfer application directly on top of TCP using Python sockets.

Rather than using a high-level networking framework or existing file-transfer protocol, the application implements its own protocol for transferring metadata and file contents.

The project progresses beyond basic socket communication by using buffered TCP stream parsing, non-blocking sockets, selector-based I/O multiplexing, per-client state management, a protocol state machine, SHA-256 integrity verification, transfer monitoring, and application-level acknowledgments.

The main purpose of the project is not simply to transfer files, but to understand the networking concepts involved in building a client-server protocol.

---

## Author

**Pragathi**

GitHub: https://github.com/Pragati-7210
