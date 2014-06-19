from litesockets import SocketExecuter, TcpClient
import time

#This starts a SocketExecuter with default of 5 threads
SE = SocketExecuter()

#This create a tcp client that points to www.google.com (its not connected yet)
client = TcpClient("www.google.com", 80)

def onRead(client):
    data = client.getRead()
    print data
    
#Now we assign a function pointer that takes 1 arg to the clients reader
client.reader = onRead

#The connection is now made, but we are not reading/writing to the socket
client.connect()

#The client can now read/write to the socket
SE.addClient(client)

#send an http request to google
client.addWrite("GET / HTTP/1.1\r\nUser-Agent: curl/7.35.0\r\nHost: www.google.com\r\nAccept: */*\r\n\r\n")
time.sleep(5)
