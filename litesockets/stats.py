from threadly import Clock

class Stats(object):
  def __init__(self):
    self.__clock = Clock()
    self.__startTime = self.__clock.accurate_time()
    self.__totalRead = 0
    self.__totalWrite = 0
  
  def getTotalRead(self):
    """
    Returns the total bytes read.
    """
    return self.__totalRead
  
  def getTotalWrite(self):
    """
    Returns the total bytes writen.
    """
    return self.__totalWrite
  
  def getReadRate(self):
    """
    Returns the bytes read per second.
    """
    X = round(self.__totalRead/(self.__clock.accurate_time() - self.__startTime), 4)
    if X > 0:
      return X
    else:
      return 0 
  
  def getWriteRate(self):
    """
    Returns the bytes written per second.
    """
    X = round(self.__totalWrite/(self.__clock.accurate_time() - self.__startTime), 4)
    if X > 0:
      return X
    else:
      return 0
  
  def _addRead(self, size):
    self.__totalRead += size
    
  def _addWrite(self, size):
    self.__totalWrite += size
    
    
def noExcept(task, *args, **kwargs):
  """
  Helper function that helps swallow exceptions.
  """
  try:
    task(*args, **kwargs)
  except:
    pass
