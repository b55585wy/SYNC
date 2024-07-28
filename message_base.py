from queue import Queue

class MessageBase:
    def __init__(self):
        self.data = dict()
    def add(self,device,data):
        if device not in self.data:
            self.data[device].put(data)
        else:
            self.data[device] = Queue()
            self.data[device].put(data)

    def get(self,device):
        if device not in self.data:
            return None
        data = self.data[device].get()
        return data
if __name__ == '__main__':

