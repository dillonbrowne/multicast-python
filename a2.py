# import socket programming library
import socket
# import thread module
import threading

clients = []  # Used to keep track of TCP connections
killServer = False  # Used to Kill UDP/TCP Server
screenlock = threading.Semaphore(value=1)  # Used to ensure printing works

if not hasattr(__builtins__, 'raw_input'):
    raw_input = input


# thread fuction
def listenToClientTCP(connection):
    global killServer
    global screenlock
    global clients

    clientAddress = connection.getpeername()
    while True:
        try:
            data = connection.recv(256)
            data = data if hasattr(__builtins__, 'raw_input') else data.decode()

            if not data.endswith('\n'): break
            screenlock.acquire()
            print(clientAddress, 'sent::::', data)
            screenlock.release()

            if data == 'hello\n': data = 'world\n'
            if data == 'goodbye\n':
                data = 'farwell\n'
                # connection closed
                screenlock.acquire()
                print('sending::::', data)
                screenlock.release()
                data = data if hasattr(__builtins__, 'raw_input') else data.encode()
                connection.send(data)
                break
            if data == 'exit\n':
                data = 'ok\n'

                screenlock.acquire()
                print('sending::::', data)
                screenlock.release()
                data = data if hasattr(__builtins__, 'raw_input') else data.encode()
                connection.send(data)
                killServer = True
                break

            screenlock.acquire()
            print('sending::::', data)
            screenlock.release()
            # Send the data
            data = data if hasattr(__builtins__, 'raw_input') else data.encode()
            connection.send(data)

        except:
            break
    clients.remove(connection)
    connection.close()


def startServerTCP(host, port):
    global killServer
    global clients
    serverAddress = (host, port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    print('starting up on', serverAddress)
    sock.bind(serverAddress)

    # put the socket into listening mode
    sock.listen(5)
    sock.settimeout(0.2)

    print("Socket is listening")

    # a forever loop until client wants to exit
    while not killServer:
        # establish connection with client
        try:
            client, addr = sock.accept()
            clients.append(client)
            # lock acquired by client

            screenlock.acquire()
            print('Connected to :', addr[0], ':', addr[1])
            screenlock.release()

            # Start a new thread
            threading.Thread(target=listenToClientTCP, args=(client,)).start()
        except:
            pass
    for c in clients:
        c.close()
    sock.close()


def startClientTCP(host, port):
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect the socket to the port where the server is listening
    serverAddress = (host, port)
    try:
        sock.connect(serverAddress)
    except:
        print("Err... Connection to server could not be made.")
        return

    try:
        while True:
            # Send data
            message = raw_input("Tpye a message to send::: ")
            if len(message) > 255:
                print('Message too large... not sending')
                continue
            message += '\n'
            message_orig = message
            print('sending::::', message)
            try:
                message = message if hasattr(__builtins__, 'raw_input') else message.encode()
                status = sock.send(message)
            except:
                print('Failed to send message...')
                status = 0

            if status == 0:
                print('Server disconnected... closing connection.')
                break

            data = sock.recv(256)
            data = data if hasattr(__builtins__, 'raw_input') else data.decode()
            print('received::::', data)
            if message_orig == 'exit\n' or message_orig == 'goodbye\n':
                print('Exiting...')
                break

    except:
        pass
    finally:
        sock.close()


sockUDP = None  # Used so multithreading will work with UDP


def startServerUDP(host, port):
    global killServer
    global sockUDP
    serverAddress = (host, port)
    sockUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print('starting up on', serverAddress)
    sockUDP.bind(serverAddress)
    sockUDP.settimeout(0.2)

    print("Socket is listening")

    # a forever loop until client wants to exit
    while not killServer:
        try:
            # establish connection with client
            msg, addr = sockUDP.recvfrom(256)  # 256 bytes max
            # Start a new thread
            threading.Thread(target=sendToClientUDP, args=(msg, addr,)).start()
        except socket.timeout:
            pass
        except:
            print("failed to recv")

    sockUDP.close()


def sendToClientUDP(message, address):
    global sockUDP
    global killServer

    try:
        data = message if hasattr(__builtins__, 'raw_input') else message.decode()

        if not data.endswith('\n'): return
        screenlock.acquire()
        print(address, 'sent::::', data)
        screenlock.release()

        if data == 'hello\n': data = 'world\n'
        if data == 'goodbye\n':
            data = 'farwell\n'
            # UDP doesnt have close connection
            # Not sure what they want...
        if data == 'exit\n':
            data = 'ok\n'
            killServer = True

        screenlock.acquire()
        print('sending::::', data)
        screenlock.release()
        try:
            data = data if hasattr(__builtins__, 'raw_input') else data.encode()
            sockUDP.sendto(data, address)
        except:
            pass

    except:
        return


def startClientUDP(host, port):
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    clientSocket.settimeout(5.0)  # try for a second before disconnecring
    addr = (host, port)

    while True:
        # Send data
        message = raw_input("Tpye a message to send::: ")
        if len(message) > 255:
            print('Message too large... not sending')
            continue
        message += '\n'
        message_orig = message
        print('sending::::', message)

        try:
            message = message if hasattr(__builtins__, 'raw_input') else message.encode()
            clientSocket.sendto(message, addr)
        except:
            print("Unable to send message... Exiting...")
            break
        try:
            data, server = clientSocket.recvfrom(256)
            data = data if hasattr(__builtins__, 'raw_input') else data.decode()
        except:
            print("Unable to receive message... Exiting...")
            break

        print('received::::', data)
        if message_orig == 'exit\n' or message_orig == 'goodbye\n':
            print('Exiting...')
            break
