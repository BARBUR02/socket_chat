from datetime import datetime
from queue import Queue
import socket

from utils import User, UserPayload, log_to_server

ACTIVE_CONNECTIONS: dict[User, socket.socket] = {}


def close_active_tcp_connections() -> None:
    for client_socket in list(ACTIVE_CONNECTIONS.values()):
        client_socket.close()


def handle_tcp_client_connection(
    client_socket: socket.socket,
    client_address: tuple[str, str],
    user: User,
    messages_queue: Queue[UserPayload],
) -> None:
    remote_address, remote_port = client_address
    log_to_server(
        f"Got new connection request on remote {remote_address}:{remote_port}. Waiting for nick followup ..."
    )

    user.username = client_socket.recv(1024).decode()
    log_to_server(f"User registered: ID:{user.id}, USERNAME:{user.username}")
    client_socket.send(f"{user.id}|{user.username}".encode())

    messages_queue.put(
        UserPayload(
            -1, "[SERVER]", f"{user.username} has joined the chat", datetime.now()
        )
    )

    while True:
        raw_payload = client_socket.recv(1024)
        if not raw_payload:
            break
        payload = UserPayload.parse(raw_payload.decode())
        messages_queue.put(payload)

    log_to_server(
        f"Cleaning up socket connection for USER: {user.username}, {remote_address}:{remote_port}..."
    )
    client_socket.close()
    ACTIVE_CONNECTIONS.pop(user)
    messages_queue.put(
        UserPayload(
            -1, "[SERVER]", f"{user.username} has left the chat", datetime.now()
        )
    )


def publisher_thread(
    messages_queue: Queue[UserPayload], udp_server_socket: socket.socket
) -> None:
    while True:
        outbound_message = messages_queue.get()
        if not outbound_message:
            break
        raw_message = outbound_message.serialize().encode()
        for client, client_socket in ACTIVE_CONNECTIONS.items():
            if client.username and client.id != outbound_message.user_id:
                if outbound_message.udp:
                    udp_server_socket.sendto(raw_message, client_socket.getpeername())
                else:
                    client_socket.send(raw_message)


def handle_udp_client_connection(
    messages_queue: Queue[UserPayload], udp_server_socket: socket.socket
) -> None:
    while True:
        raw_payload, _ = udp_server_socket.recvfrom(1024)
        if not raw_payload:
            break
        payload = UserPayload.parse(raw_payload.decode())
        messages_queue.put(payload)
