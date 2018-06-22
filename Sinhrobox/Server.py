from os import walk
from os.path import getmtime
import ConfigParser
import io
import socket
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
import thread
import json
import hashlib


def loadTCPConfiguration():
    with open("serverconf.ini") as f:
        configFile = f.read()
    configuration = ConfigParser.RawConfigParser(allow_no_value=True)
    configuration.readfp(io.BytesIO(configFile))
    directory = configuration.get('paths', 'rootdir')
    serverAddress = configuration.get('server', 'ip')
    serverPort = configuration.get('server', 'port')
    return directory, serverAddress, serverPort


def loadSFTPCOnfiguration():
    with open("serverconf.ini") as f:
        configFile = f.read()
    configuration = ConfigParser.RawConfigParser(allow_no_value=True)
    configuration.readfp(io.BytesIO(configFile))
    directory = configuration.get('paths', 'rootdir')
    serverAddress = configuration.get('sftp', 'sftpIp')
    serverPort = configuration.get('sftp', 'port')
    user = configuration.get('sftpUsers', 'user1')
    pwd = configuration.get('sftpUsers', 'password1')
    return directory, serverAddress, serverPort, user, pwd


def getFileList(directory):
    fileList = {}
    for (directoryPath, directoryName, fileName) in walk(directory):
        for name in fileName:
            fileDictionary = {}
            fileWithPath = directoryPath + '/' + name
            fileDateTime = getmtime(fileWithPath)
            fileDictionary['fileModified']=fileDateTime
            fileDictionary['hashValue']=getFileHash(fileWithPath)
            fileList[fileWithPath] = fileDictionary
    return fileList

def getFileHash(filePath):
    f = open(filePath,'rb')
    contents = f.read()
    sha256Checksum = hashlib.sha256(contents).hexdigest()
    return sha256Checksum

def startTCPServer(directoryPath, serverAddress, serverPort):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    address = (serverAddress, int(serverPort))
    sock.bind(address)
    sock.listen(1)
    while True:
        print("starting TCP")
        connection, clientAddress = sock.accept()
        try:
            while True:
                data = connection.recv(1024)
                if data:
                    listOfFiles = getFileList(directoryPath)
                    dataString = json.dumps(listOfFiles)
                    connection.sendall(dataString)
                else:
                    break
        finally:
            connection.close()


def startSFTPServer(directory, serverAddress, serverPort, userName, pwd):
    serverAuthorizer = DummyAuthorizer()
    serverAuthorizer.add_user(userName, pwd, directory, perm='elradfmwMT')
    handler = FTPHandler
    handler.authorizer = serverAuthorizer
    server = FTPServer((serverAddress, serverPort), handler)
    server.serve_forever()


if __name__ == "__main__":
    try:
        directory, serverAddress, serverPort = loadTCPConfiguration()
        thread.start_new_thread(startTCPServer, (directory, serverAddress, serverPort))
        directory, serverAddress, serverPort, user, pwd = loadSFTPCOnfiguration()
        thread.start_new_thread(startSFTPServer, (directory, serverAddress, serverPort, user, pwd))
    except:
        print "Error starting servers"
    while True:
        pass
