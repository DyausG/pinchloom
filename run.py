"""Local/offline launcher for the existing AeroPuzzle adaptation."""
import os
from pathlib import Path
import socket
import sys
ROOT=Path(__file__).resolve().parent
os.environ.setdefault('MPLCONFIGDIR',str(ROOT/'cache'/'matplotlib'))
os.environ['TF_CPP_MIN_LOG_LEVEL']='3'
os.chdir(ROOT)
sys.path.insert(0,str(ROOT/'aeropuzzle_game'))
# Only this process is isolated; this does not alter Windows networking.
_connect=socket.socket.connect
_connect_ex=socket.socket.connect_ex
def local(address):return isinstance(address,tuple) and address[0] in ('127.0.0.1','localhost','::1')
def connect(sock,address):
    if not local(address):raise OSError('AeroPuzzle offline launcher: external networking disabled')
    return _connect(sock,address)
def connect_ex(sock,address):return _connect_ex(sock,address) if local(address) else 10013
socket.socket.connect=connect;socket.socket.connect_ex=connect_ex
from aeropuzzle.main import main
if __name__=='__main__':main()
