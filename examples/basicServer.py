from litesockets import SocketExecuter, TcpServer
import time

#This starts a SocketExecuter with default of 5 threads
SE = SocketExecuter()

#creates a tcpServer listening on localhost port 11882 (socket is not open yet)
server = TcpServer("localhost", 11882)

#This is ran once the far side is connected
def newConnection(client):
    print "Got new TCPClient", client
    #need to add the client to the SocketExecuter to be able to do anythign with it
    SE.addClient(client)
    client.addWrite("hello\n")
    #if we wanted to check for incoming data we would add a reader to the client
    time.sleep(.01)
    #End the clients connection
    client.end()
    
#We assign a fuction with 1 argument that will get a client for the server
server.onNew = newConnection

#The socket is not open, but will not yet accept anything
server.connect()

#The server will now accept clients that connect to its listen socket
SE.addServer(server)

time.sleep(100000)

