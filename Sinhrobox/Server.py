import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from socket import *
import pysftp as sftp
import os
cnopts = sftp.CnOpts()
cnopts.hostkeys = None
veza = sftp.Connection('192.168.1.11', username='jurab', password ='jurabaksa', cnopts = cnopts)
remotepath='/home/jurab/sinhrobox'
localpath='D:\sinhrobox'


#Funkcija za upload putem SFTP
def sftpUpload(imedatoteke):
    try:
        veza.put(localpath + '\\' +imedatoteke,remotepath+'/'+imedatoteke)
        veza.close
    except Exception, e:
        print "failed to upload", str(e)

#Funkcija za SFTP download
def sftpDownload(imedatoteke):
    try:
        veza.get(remotepath+'/'+imedatoteke, localpath+'\\'+imedatoteke)
        veza.close
    except Exception, e:
        print 'failed to download', str(e)

def sftpDownloadMape():
    try:
        veza.get_d(remotepath, localpath)
        veza.close
    except Exception, e:
        print 'failed to download folder', str(e)

#Nadziranje mape na lokalnom disku
class Watcher:
    DIRECTORY_TO_WATCH = "D:\\sinhrobox"
    def __init__(self):
        self.observer = Observer()

    def run(self):
        event_handler = Handler()
        self.observer.schedule(event_handler, self.DIRECTORY_TO_WATCH, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(5)
        except:
            self.observer.stop()
            print "Error"

        self.observer.join()

    
#Upravljanje dogadajima
class Handler(FileSystemEventHandler):
    @staticmethod
    def on_any_event(event):
        
        DIRECTORY_TO_WATCH="D:\\sinhrobox" 
        duljina = len(DIRECTORY_TO_WATCH)+1
        ime_datoteke_upload = event.src_path[duljina:]
        ime_datoteke = event.src_path[duljina:]

        if event.is_directory:
            return None

        elif event.event_type == 'modified':# or event.event_type == 'created':
            # Ako je datoteka KREIRANA ILI MODIFICIRANA
            print "Kreirana je ili izmjenjena datoteka: - %s." % ime_datoteke_upload
            print "Uploadam %s na server" %ime_datoteke_upload
            sftpUpload(ime_datoteke_upload) 
            print "Uploaded"
            
        elif event.event_type == 'deleted':
            # Ako je datoteka BRISANA
            print "Obrisana datoteka: -%s" %event.src_path
            print "Brisem sa servera: -%s" %ime_datoteke_upload         
            """
            BRISANJE DATOTEKE - Ovaj dio bi trebao brisati datoteku na serveru ukoliko se obrise na lokalnom disku"""
            string = 'rm "' + remotepath + '/' +ime_datoteke + '"'
            print ('izvrsavam %s') %string
            
            try: veza.execute(string)
            except Exception, e:
                print 'Brisanje neuspjesno', str (e)
         #preimenovanje datoteke   
        elif event.event_type == 'moved':
            novo_ime_datoteke = event.dest_path[duljina:]
            string = 'mv "' + remotepath + '/' +ime_datoteke + '" "'+remotepath + '/' + novo_ime_datoteke + '"'
            print "Preimenovana ili premjestena datoteka iz%s u -%s" %(ime_datoteke_upload,novo_ime_datoteke)
            print string
            veza.execute(string)
        

if __name__ == '__main__':
    mod_rada = raw_input('Mod rada 0 - upload i odasiljanje mape serveru ili 1-sinhronizacija sa serverom 2-download kompletne mape (0/1/2):')

    if mod_rada == '0':
        print ('nadzirem')
        w = Watcher()
        w.run()
        
    elif mod_rada == '1':
        putanja = '/home/jurab/sinhrobox'
        dulj = len (putanja)
        serverName = '192.168.1.11'
        serverPort = int(raw_input('broj porta: '))
        print 'Aplikacija èeka na promjene servera'
        clientSocket = socket (AF_INET, SOCK_STREAM)
        try:
            while 1:
                clientSocket.connect((serverName, serverPort))
                poruka = clientSocket.recv(1024)
                print 'primljeno'
                print 'poruka je :%s' %poruka
                kod = poruka[:1]
                print 'kod = %s' %kod
                putanja_datoteke_na_serveru = poruka[1:]
                print 'putanja = %s' %putanja_datoteke_na_serveru
                ime_datoteke_na_serveru = putanja_datoteke_na_serveru[dulj+1:]
                print ('ime datoteke na serveru = %s') %ime_datoteke_na_serveru
                if kod == '1':
                    sftpDownload(ime_datoteke_na_serveru)
                    print 'preuzeta datoteka :%s ' %ime_datoteke_na_serveru
                if kod == '2':
                    print 'obrisana' %ime_datoteke_na_serveru
                    putanja = localpath+'\\'+ime_datoteke_na_serveru
                    print putanja
                    os.remove(putanja)
        except Exception as e:
            print 'keyboard interrupt'
            print e
            clientSocket.close()
    elif mod_rada == '2':
        sftpDownloadMape()
        
