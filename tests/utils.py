import time

class testClass():
  def __init__(self, SE):
    self.__clients = list()
    self.reads = list()
    self.read_len = 0
    self.__socketExecuter = SE

  def read(self, client):
    data = client.getRead()
    #print "read Data", len(data)
    self.reads.append(data)
    self.read_len+=len(data)

  def accept(self, client):
    print "New client", client
    self.__clients.append(client)
    client.__reader = self.read
    client.closer = self.remove
    self.__socketExecuter.addClient(client)

  def remove(self, client):
    print "removing Client", client
    try:
      self.__clients.pop(self.__clients.index(client))
    except Exception as e:
      print "client not in list", e
      print self.__clients


def waitTill(F, V, T):
  c = 0
  while F(V) and c < T:
    time.sleep(.01)
    c+=1
