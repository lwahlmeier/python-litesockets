# litesockets
litesockets is a simple thread safe concurrent networking library.  The main design is for either servers or load tools.  

It helps manage many connections, forcing each connection to process in order but allowing any indivdial connections to work independantly.

## Basics
There are 3 main objects that you deal with in litesockets.

* **SocketExecuter** - Processes all network connections enforcing each connection to be handled in order.  This is used by all connection types.
* **Server** - Servers open listen ports and create Clients when a connection is esstablished.
* **Client** - These are the actual connections that are read/written to.

Every connection type has an implementation of Client/Server (UdpClient/TcpClient/SSLServer).
### Creating a simple Client

```python
from litesockets import SocketExecuter
import time

#This starts a SocketExecuter with default of 5 threads
SE = SocketExecuter()

#This create a tcp client that points to www.google.com (its not connected yet)
client = SE.createTcpClient("www.google.com", 80)

def onRead(client):
    data = client.getRead()
    print data
    
def onClose(client):
    print "Client closed, ", client
            
#Now we assign a function pointer that takes 1 arg to the clients reader
client.setReader(onRead)
client.addCloseListener(onClose)

#To Connect the socket call .connect(), once the connection is made when data is sent the read callback will be called
client.connect()

#send an http request to google
client.addWrite("GET / HTTP/1.1\r\nConnection: close\r\nUser-Agent: curl/X.XX.0\r\nHost: www.google.com\r\nAccept: */*\r\n\r\n")
time.sleep(5)

```
        
At this point you should the http/html output from www.google.com.
        
### Createing a simple Server

```python
from litesockets import SocketExecuter
import time

#This starts a SocketExecuter with default of 5 threads
SE = SocketExecuter()

#creates a tcpServer listening on localhost port 11882 (socket is not open yet)
server = SE.createTcpServer("localhost", 11882)

#clients read callback
def onRead(client):
    data = client.getRead()
    print data

#This is ran once the far side is connected
def onNewConnection(client):
    print "Got new TCPClient", client
    #need to add the client to the SocketExecuter to be able to do anythign with it
    client.setReader(onRead)
    client.addWrite("hello\n")
    #if we wanted to check for incoming data we would add a reader to the client
    time.sleep(.01)
    #Close the clients connection
    client.close()
        
#We assign a fuction with 1 argument that will get a client for the server
server.setOnClientnewConnection)
        
#The socket is not open, but will not yet accept anything
server.start()
        
time.sleep(120)
```
        
If you now ran "telnet localhost 11882" you would get the message "hello" and then disconnected






