from datetime import datetime
import socket

from utils import (
    MCAST_GRP,
    MCAST_PORT,
    MULTICAST_INDICATOR,
    UDP_INDICATOR,
    UserPayload,
    log_to_server,
    move_input_down,
)


CLIENT_SOCKETS = []


def close_client_sockets():
    for socket in CLIENT_SOCKETS:
        socket.close()


def writer_thread(
    tcp_server_socket: socket.socket,
    udp_client_socket: socket.socket,
    multicast_send_socket: socket.socket,
    server_address: tuple[str, int],
    user_id: int,
    username: str,
):
    while True:
        message = input()
        if message == "!disconnect":
            close_client_sockets()
            break
        message_payload = UserPayload(user_id, username, message, datetime.now())
        if message.startswith(UDP_INDICATOR):
            message_payload.udp = True
            message_payload.message = message_payload.message[len(UDP_INDICATOR) :]
            udp_client_socket.sendto(
                message_payload.serialize().encode(), server_address
            )
        elif message.startswith(MULTICAST_INDICATOR):
            message_payload.message = message_payload.message[
                len(MULTICAST_INDICATOR) :
            ]

            multicast_send_socket.sendto(
                message_payload.serialize().encode(), (MCAST_GRP, MCAST_PORT)
            )

        else:
            tcp_server_socket.send(message_payload.serialize().encode())

        move_input_down(UserPayload(**{**message_payload.__dict__, "username": "YOU"}))


def tcp_listener_thread(
    tcp_client_socket: socket.socket, udp_client_socket: socket.socket
) -> None:
    while True:
        raw_payload = tcp_client_socket.recv(1024)
        if not raw_payload:
            close_client_sockets()
            log_to_server(
                "Server closed the connection, click [ENTER] to exit", "ERROR"
            )
            break
        raw_payload = raw_payload.decode()
        payload = UserPayload.parse(raw_payload)
        move_input_down(payload, external=True)


def udp_listener_thread(udp_client_socket: socket.socket) -> None:
    while True:
        raw_payload, _ = udp_client_socket.recvfrom(1024)
        if not raw_payload:
            log_to_server(
                "Server closed the connection, click [ENTER] to exit", "ERROR"
            )
            break
        raw_payload = raw_payload.decode()
        payload = UserPayload.parse(raw_payload)
        move_input_down(payload, external=True)


def multicast_listener_thread(
    multicast_client_socket: socket.socket, user_id: int
) -> None:
    while True:
        raw_payload, _ = multicast_client_socket.recvfrom(1024)
        if not raw_payload:
            break
        payload = UserPayload.parse(raw_payload.decode())
        if payload.user_id == user_id:
            continue

        move_input_down(payload, external=True)
