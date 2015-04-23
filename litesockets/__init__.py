from socketexecuter import SocketExecuter
from udp import UdpClient, UdpServer
from tcp import TcpClient, TcpServer
from sslSockets import SSLClient, SSLServer
from threadly import Singleton

print Singleton
print SocketExecuter
class GlobalSocketExecuter(Singleton.Singleton, SocketExecuter):
  """
  This is a Singleton instance of a SocketExecuter.  This is not constructed until created for the first time
  at which point it will last for the duration of the python process.  

  This is used as a convenience
  """

  def __init__(self):
    SocketExecuter.__init__(self)


