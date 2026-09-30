# TCP Network File Transfer System

A TCP-based client-server file transfer system built from scratch in Python using sockets.

The project demonstrates core computer networking concepts including TCP communication, socket programming, application-layer protocol design, message framing, non-blocking I/O, I/O multiplexing with `selectors`, SHA-256 integrity verification, and application-level acknowledgments.

## Features

- TCP client-server communication
- IPv4 socket programming
- Custom application-layer protocol
- File transfer using chunks
- Non-blocking sockets
- I/O multiplexing using Python `selectors`
- Multiple client connections
- Per-client protocol state
- TCP stream framing
- SHA-256 file integrity verification
- Application-level `OK` / `FAILED` acknowledgment
- Transfer progress and throughput measurement

## Architecture

```text
                    CLIENT
                      |
                      | TCP connection
                      |
                      v
                   SERVER
                      |
              +-------+-------+
              |               |
          Selector        ClientState
              |               |
              v               v
          Event Loop      Protocol State
                              |
                              v
                       Receive File
                              |
                              v
                        SHA-256 Check
                              |
                    +---------+---------+
                    |                   |
                  MATCH              MISMATCH
                    |                   |
                    v                   v
                   OK                FAILED
                    |
                    v
                  CLIENT
