
class Db:
    def __init__(self):
        self.data=[]

    def clear(self):
        self.data=[]

    def add(self,data):
        self.data.append(data)

    def end_add(self):
        pass
        
    def get_all(self):
        out=[]
        for x in self.data:
            out.append(x[:-1])
        return out

    def get_thumb(self,path):
        for x in self.data:
            if x[0]==path:return x[4]

    def set(self,data):
        for n,x in enumerate(self.data):    
            if x[0]==data[0]:
                th=self.data[n][-1]
                self.data[n]=[data[0],data[1],data[2],data[3],th]

