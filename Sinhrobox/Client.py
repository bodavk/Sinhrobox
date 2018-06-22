from os import walk
from os.path import getmtime
import ConfigParser
import io
import os
import socket
import json
import time
import hashlib
from ftplib import FTP

def loadConfiguration():
    with open("clientconf.ini") as f:
        configFile = f.read()
    configuration = ConfigParser.RawConfigParser(allow_no_value=True)
    configuration.readfp(io.BytesIO(configFile))
    directory = configuration.get('path', 'localdir')
    serverDirectory = configuration.get('path', 'directory')
    serverAddress = configuration.get('tcp', 'ip')
    serverPort = configuration.get('tcp', 'port')
    sftpAddress = configuration.get('sftp', 'sftpIp')
    sftpPort = configuration.get('sftp', 'sftpPort')
    username = configuration.get('user', 'user1')
    password = configuration.get('user', 'password1')
    timer = configuration.get('schedule', 'timer')
    return directory, serverDirectory, serverAddress, serverPort, sftpAddress, sftpPort, username, password, timer


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

def getServerFileList(address, port):
    timeout = 3
    totalData = []

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serverAddress = (address, int(port))
    sock.connect(serverAddress)

    try:
        sock.sendall("init")
    except socket.error:
        print socket.error.message

    beginTime = time.time()
    while True:
        if totalData and time.time() - beginTime > timeout:
            break
        elif time.time() - beginTime > timeout * 2:
            break
        try:
            data = sock.recv(4096)
            if data:
                totalData.append(data)
        except:
            pass
        finally:
            sock.close()

    dataReceived = ''.join(totalData)
    filelist = json.loads(dataReceived)
    return filelist

def stripRootDir(fileName, rootDirString):
    return fileName[0 + len(rootDirString):]

def listContainsFile(listOfFiles, fileName, fileNamePath, itemPath):
    for file in listOfFiles:
        if stripRootDir(file, itemPath).encode('utf-8') == stripRootDir(fileName, fileNamePath).encode('utf-8'):
            return True, file
    return False, None

def getFileDateAndHash(fileName, fileList):
    date = fileList.get(fileName).get('fileModified')
    hash = fileList.get(fileName).get('hashValue')
    return date,hash

def fileChanged(fileListRemote, fileListLocal, localFileName, remoteFileName):
    remoteFileDate, remoteFileHash = getFileDateAndHash(remoteFileName, fileListRemote)
    localFileDate, localFileHash = getFileDateAndHash(localFileName, fileListLocal)
    if localFileHash == remoteFileHash:
        return 0
    elif localFileDate > remoteFileDate:
        return 1
    else:
        return 2

def setFTPConnection(userName, password, sftpServerAddress, serverPort, localPath):
    ftp = FTP('')
    ftp.connect(sftpServerAddress, serverPort)
    ftp.login(userName,password)
    return ftp

def uploadLocalFileToRemote(fileName, connection, localDirectory):
    strippedName = stripRootDir(fileName, localDirectory)
    strippedName = strippedName[1:]
    os.chdir(localDirectory)
    try:
        connection.storbinary('STOR '+strippedName, open(strippedName, 'rb'))
        print("Uploaded -"+strippedName)
    except Exception, e:
        print(str(e))
    finally:
        connection.quit()

def downloadFileFromRemote(strippedName, connection, localDirectory):
    os.chdir(localDirectory)
    try:
        localFile = open(localDirectory+"/"+strippedName, 'wb')
        connection.retrbinary('RETR '+strippedName, localFile.write, 1024)
        print ("Downloaded - "+ strippedName)
    except Exception, e:
        print(str(e))
    finally:
        connection.quit()
        localFile.close()


def synchronize(directory, serverDirectory, serverAddress, serverPort, sftpAddress, sftpPort, username, password):
    fileListRemote = getServerFileList(serverAddress, serverPort)
    fileListLocal = getFileList(directory)
    for item in fileListLocal:
        containsFile, fileName =  listContainsFile (fileListRemote,item,directory,serverDirectory)
        if containsFile:
            connection = setFTPConnection(username, password, sftpAddress, sftpPort, directory)
            fileAge = fileChanged(fileListRemote, fileListLocal, item, fileName)
            try:

                if fileAge == 1:
                    uploadLocalFileToRemote(item, connection, directory)
                elif fileAge == 2:
                    strippedName = stripRootDir(item, directory)
                    downloadFileFromRemote(strippedName, connection, directory)
                else:
                    print "No changes in files"
            except Exception, e:
                print(str(e))
        # TODO take into two methods - check whatLocalHasServerDoesnt and check whatServerHasAndLocalDoesnt
        else:
            connection = setFTPConnection(username, password, sftpAddress, sftpPort, directory)
            uploadLocalFileToRemote(item, connection, directory)
    for item in fileListRemote:
        fileListLocal = getFileList(directory)
        containsFile, fileName = listContainsFile(fileListLocal, item, serverDirectory, directory)
        if not containsFile:
            connection = setFTPConnection(username, password, sftpAddress, sftpPort, directory)
            strippedName = stripRootDir(item,serverDirectory)
            downloadFileFromRemote(strippedName,connection,directory)

if __name__ == "__main__":
    directory, serverDirectory, serverAddress, serverPort, sftpAddress, sftpPort, username, password, timer = loadConfiguration()
    while True:
        timerStart = time.time()
        synchronize(directory, serverDirectory, serverAddress, serverPort, sftpAddress, sftpPort, username, password)
        timerFinished = time.time()
        timePassed = timerFinished - timerStart
        sleepingTime = int(timer) - timePassed
        print("Sleeping for "+ str(sleepingTime))
        time.sleep(sleepingTime)
