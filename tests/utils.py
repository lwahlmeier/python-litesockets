from __future__ import print_function
import time

class testClass():
  def __init__(self, SE, name="MAIN"):
    self.clients = list()
    self.name =name
    self.reads = list()
    self.read_len = 0
    self.socketExecuter = SE

  def read(self, client):
    data = client.getRead()
    #print self.name+":read Data", len(data)#, data
    self.reads.append(data)
    self.read_len+=len(data)

  def accept(self, client):
#    print("New client", client)
    self.clients.append(client)
    client.setReader(self.read)
    client.addCloseListener(self.remove)
    #client.connect()

  def remove(self, client):
    try:
      self.clients.pop(self.clients.index(client))
    except Exception as e:
      print("client not in list", e)
      print(self.clients)


def waitTill(F, V, T):
  t = time.time()*1000
  while F(V) and (time.time()*1000)-t < T:
    time.sleep(.1)
