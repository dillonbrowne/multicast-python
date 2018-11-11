import socket  # used to start udp server/client
import threading  # used to send and recv data using threads
import math  # will be used for ceiling function
import hashlib  # used to generate the hash, will usw md5 for simplicity
import os  # used to get the file size
import time  # used to sleep, will remove
import re  # used for regex with ack
import logging as log

fileBlocks = []
killServer = False
numBlocks = None
sockUDP = None
clientSocket = None
ack = re.compile("ACK\d+")
nack = re.compile("NACK\d+")


def clientRUDP(host, port, f, n):
    print(f'Will Send {n} times befor checking ack')
    # host, port, file, number packets to send at
    #       a time before checking ack status
    blockSize = 300  # max data per block is to be safe with data transfer
    # allows room for headder
    # max udp block size of data is 508 bytes,
    #      chose 300 in case headder has more data
    #      allows for a custom headder to be 208 bytes, including the newline
    fileSize = os.path.getsize(f.name)
    # f.name gets the file path
    # size will be used to determine the number of blocks needed.
    # max file size will be 128*blockSize
    numBlocks = math.ceil(fileSize / blockSize)
    maxFileSize = blockSize * 128
    if numBlocks > 128:
        print(f'File too large max file allowed is {maxFileSize} Bytes')
        # Make sure the file is not too large
        # return -1 indicating an error
        return -1
    lastUnAck = 0  # Used to keep track of the last un ack.
    # will be 0,1,2,3,4,5,... for n=1
    # when n > 1 it will be 0,1,2,... maybe, but could skip
    # will skip when more get ack faster than can send and update

    # set up the UDP socket
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    clientSocket.settimeout(0.2)  # try for a second before disconnecring
    addr = (host, port)  # store the address for sending/recv data

    fileBlocks = [None] * numBlocks  # used to store the file
    # allocate space for the file
    f.seek(0)
    # make sure the file pointer is at the begining of the file
    for i in range(numBlocks):
        '''  headder will be in format
         <<field>>=<<value>>,<<field>>=<<value>>,...\n
         fields seperated by comma, ended with new line
         will be used like a dictionary '''
        block = f.read(blockSize)
        ''' loads the block into memory
            blocks start counting at 0  '''
        blockHash = hashlib.md5(block).hexdigest()
        ''' Any block with same hash should have same data
            MD5 is known to have some overlap, but will work for this
            to make blocks with the same data  '''
        headder = f'block={i},total={numBlocks},hash={blockHash}\n'
        # order doesn't matter for the headder.  It will be parsed
        # fields not implimented are ignored
        blockData = b"".join([headder.encode(), block])
        # Combines the block with the headder, which is of type byte
        fileBlocks[i] = blockData
        # Store the data in a list that has the blocks

    nackBlock = None
    ackBlock = None

    while lastUnAck < numBlocks:
        num = 0
        offset = 0
        while num < n:
            blockToSend = lastUnAck + offset
            if blockToSend >= numBlocks:
                break
            if fileBlocks[blockToSend] is None:
                offset += 1
                continue
            message = fileBlocks[blockToSend]
            clientSocket.sendto(message, addr)
            offset += 1
            num += 1
        for i in range(n):
            try:
                block, addr = clientSocket.recvfrom(50)  # Can get a message that is 508 bytes max
                status, blockNum = checkACK(block)
                if status:
                    fileBlocks[blockNum] = None
                    if blockNum == numBlocks: print(f'Block {numBlocks}')
            except socket.timeout:
                pass
        while lastUnAck < numBlocks:
            if fileBlocks[lastUnAck] is None:
                lastUnAck += 1
            else:
                break


def checkACK(block):
    data = block.decode()
    if ack.match(data):
        ackBlock = int(data[3:])
        # print(f'Block {ackBlock} was ack by server')
        return True, ackBlock
    elif nack.match(data):
        nackBlock = data[4:]
        # print(f'Block {nackBlock} will be resent')
        return False, nackBlock
    else:
        print('Invalid response recieved...')
        print(f'Expected ACK# or NACK#, recieved {data}')
        return False, None


def serverRUDP(host, port, f, n):
    global numTimes
    global sockUDP
    serverRecBlock = [None] * n

    sockUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    serverAddress = (host, port)
    print('RUDP server starting up on', serverAddress)
    sockUDP.bind(serverAddress)
    # Server is started
    sockUDP.settimeout(0.5)  # timeout after 0.5 seconds
    addr = None
    while not killServer:
        i = 0
        while i < n:
            try:
                block, addr = sockUDP.recvfrom(508)  # Can get a message that is 508 bytes max
                serverRecBlock[i] = block
                i += 1
            except socket.timeout:
                serverRecBlock[i] = None
                i += 1 if i != 0 else 1
        for i in range(n):
            if serverRecBlock[i] is not None:
                checkBlock(serverRecBlock[i], addr)
                serverRecBlock[i] = None
        for i in range(n): serverRecBlock[i] = None

    for block in fileBlocks:
        f.write(block)
    f.close()


numTimes = None


def checkBlock(block, addr):
    global fileBlocks
    global killServer
    global numBlocks
    global sockUDP
    global numTimes

    blockLen = len(block)

    header = {}
    field = ''
    data = ''
    isData = False
    dataStart = None
    for i in range(blockLen):
        c = block[i:i + 1]
        c = c.decode()

        # end of header
        if c == '\n':
            # specify where data starts
            dataStart = i + 1
            if field not in header and field != '':
                header[field] = data
            break
        if c == ',':
            if field == '': continue
            if field not in header:
                header[field] = data
            data = None
            field = ''
            isData = False
            continue
        if c == '=':
            if field == '': continue
            data = ''
            isData = True
            continue

        if not isData:
            field += c
        else:
            data += c
    blockData = block[dataStart:]
    blockHash = hashlib.md5(blockData).hexdigest()
    if 'block' in header:
        blockNum = int(header['block'])
    else:
        blockNum = 0
    if 'total' in header:
        if numBlocks is None:
            numBlocks = int(header['total'])
            fileBlocks = [None] * numBlocks
            numTimes = [0] * numBlocks
        elif numBlocks != int(header['total']):
            print('Total Block mismatch')
    actualHash = None if 'hash' not in header else header['hash']
    if actualHash != blockHash:
        print('-----------------------')
        print('given hash: ', header['hash'])
        print('expected  : ', blockHash)
        print('-----------------------')
        msg = f'NACK{blockNum}'
        sockUDP.sendto(msg.encode(), addr)
    elif fileBlocks[blockNum] is None:
        msg = f'ACK{blockNum}'
        sockUDP.sendto(msg.encode(), addr)
        fileBlocks[blockNum] = blockData
        numTimes[blockNum] += 1
        # print(f'Recvd Block {blockNum}')
    else:
        msg = f'ACK{blockNum}'
        sockUDP.sendto(msg.encode(), addr)
        numTimes[blockNum] += 1
        # print(f'Recvd Block {blockNum} again')
        # Send ACK again, but ignore data
        # Already had data

    if fileBlocks is not None and blockNum == numBlocks - 1: killServer = True

