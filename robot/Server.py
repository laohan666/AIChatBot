from SocketServer import ThreadingTCPServer, BaseRequestHandler
from rasa_nlu.model import Interpreter
from scripts.rasa_robot import Robot
from warnings import filterwarnings

filterwarnings('ignore')

MODEL_ADDR = './data/models/current/nlu'
INTERPRETER = Interpreter.load(MODEL_ADDR)
HOST, PORT = "localhost", 8877


class MyTCPHandler(BaseRequestHandler):
    def handle(self):
        robot = Robot(self.request, INTERPRETER)
        while True:
            self.request.sendall('SESSIONSTOP')
            try:
                if not robot.session():
                    self.request.sendall('STOPRUNNING')
                    del robot
                    break
            except:
                self.request.sendall('There is some mistakes happended.')


if __name__ == "__main__":
    server = ThreadingTCPServer((HOST, PORT), MyTCPHandler)
    print 'server is already running at (%s:%s)' % (HOST, PORT)
    server.serve_forever()
