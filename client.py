from concurrent.futures import ThreadPoolExecutor
import socket
import struct
from client_handlers import (
    CLIENT_SOCKETS,
    close_client_sockets,
    multicast_listener_thread,
    tcp_listener_thread,
    udp_listener_thread,
    writer_thread,
)
from utils import (
    HOST,
    PORT,
    MCAST_GRP,
    MCAST_PORT,
    log_to_server,
)


def main() -> None:
    server_address = (HOST, PORT)

    tcp_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    udp_client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    multicast_send_socket = socket.socket(
        socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
    )
    multicast_receive_socket = socket.socket(
        socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP
    )
    multicast_send_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    multicast_receive_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    tcp_client_socket.connect(server_address)
    udp_client_socket.bind(tcp_client_socket.getsockname())
    multicast_receive_socket.bind((MCAST_GRP, MCAST_PORT))

    mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
    multicast_receive_socket.setsockopt(
        socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq
    )

    CLIENT_SOCKETS.extend(
        [
            tcp_client_socket,
            udp_client_socket,
            multicast_receive_socket,
            multicast_send_socket,
        ]
    )

    try:
        username = input("Provide username: ")
        tcp_client_socket.sendall(username.encode())

        server_response = tcp_client_socket.recv(1024)
        if not server_response:
            log_to_server(
                "Server closed connection while registering user. Try again later.",
                "ERROR",
            )
            return
        user_id, username = server_response.decode().split("|")

        executor = ThreadPoolExecutor()

        executor.submit(
            writer_thread,
            tcp_client_socket,
            udp_client_socket,
            multicast_send_socket,
            server_address,
            int(user_id),
            username,
        )
        executor.submit(tcp_listener_thread, tcp_client_socket, udp_client_socket)
        executor.submit(udp_listener_thread, udp_client_socket)
        executor.submit(
            multicast_listener_thread, multicast_receive_socket, int(user_id)
        )
        executor.shutdown(wait=True)
    except KeyboardInterrupt:
        log_to_server("CLICK ENTER to leave the chat.", "ERROR")
        close_client_sockets()
        executor.shutdown(wait=True)


if __name__ == "__main__":
    main()
