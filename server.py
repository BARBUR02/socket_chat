from concurrent.futures import ThreadPoolExecutor
import socket
from queue import Queue
from server_handlers import (
    ACTIVE_CONNECTIONS,
    close_active_tcp_connections,
    handle_tcp_client_connection,
    handle_udp_client_connection,
    publisher_thread,
)
from utils import HOST, PORT, ThreadSafeIncrementer, User, UserPayload, log_to_server


INCREMENTER = ThreadSafeIncrementer()


def main() -> None:
    tcp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    udp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    tcp_server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    tcp_server_socket.bind((HOST, PORT))
    udp_server_socket.bind((HOST, PORT))

    log_to_server(f"Listening on {HOST}:{PORT}")

    tcp_server_socket.listen()

    messages_queue: Queue[UserPayload] = Queue()

    executor = ThreadPoolExecutor()

    try:
        executor.submit(publisher_thread, messages_queue, udp_server_socket)
        executor.submit(handle_udp_client_connection, messages_queue, udp_server_socket)
        while True:
            client_socket, client_address = tcp_server_socket.accept()
            new_user = User(INCREMENTER.increment(), None)
            ACTIVE_CONNECTIONS[new_user] = client_socket
            executor.submit(
                handle_tcp_client_connection,
                client_socket,
                client_address,
                new_user,
                messages_queue,
            )
    except KeyboardInterrupt as e:
        log_to_server(f"Got Keyboard interrupt. Closing the server...", "ERROR")
    except Exception as e:
        log_to_server(f"Exception occurred: {e}.\nStopping server...\n", "ERROR")
    finally:
        close_active_tcp_connections()
        messages_queue.put(None)
        udp_server_socket.close()
        tcp_server_socket.close()
        executor.shutdown(wait=True)
        log_to_server(f"Server closed.", "ERROR")


if __name__ == "__main__":
    main()
