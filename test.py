import docker
import json
from docker.utils.socket import next_frame_header, read_exactly, read

client = docker.from_env()


container = None
for cnt in client.containers.list():
    print (cnt.short_id)
    if cnt.short_id == "5baedd8471":
        container = cnt
        break

if not container:
    exit(1)

def wait(socket):
    while 1:
        now = read(socket, 4096)
        if now == b'\r\n':
            continue
        print (now)
        break

"""
cmd = ["btcwallet", "-u", "bbl", "-P", "bbl", "--simnet", "--create"]
walletpass = b'lalala\n'
stdin = [walletpass, walletpass, "no", "no", "OK"]
#res = container.exec_run(["rm", "/root/.btcwallet/simnet/wallet.db"], socket=True)
#wait(res.output)
res = container.exec_run(cmd, tty=True, stdin=True, socket=True)

socket = res.output
wait(socket)
socket._sock.send(walletpass)
wait(socket)
socket._sock.send(walletpass)
wait(socket)
socket._sock.send(b'no\n')
wait(socket)
socket._sock.send(b'no\n')
wait(socket)
socket._sock.send(b'OK\n')
wait(socket)

cmd = ["btcwallet", "-u", "bbl", "-P", "bbl", "--simnet"]
res = container.exec_run(cmd, detach=True)
cmd = ["btcctl",
        "--rpcuser=bbl", "--rpcpass=bbl",
        "--wallet", "walletpassphrase", '"lalala"', "1800", "--simnet"]
res = container.exec_run(cmd, detach=True)
"""

cmd = ["btcctl",
        "--simnet", "--rpcuser=bbl", "--rpcpass=bbl",
        "--wallet", "walletpassphrase", 'lalala', "1800"]
res = container.exec_run(cmd)
print (res.output)

"""
cmd = ["btcctl", "--simnet", "--rpcuser=bbl", "--rpcpass=bbl", "--wallet", "listaccounts"]
res = container.exec_run(cmd)
print (json.loads(res.output.decode('utf-8')))

cmd = ["btcctl", "--simnet", "--rpcuser=bbl", "--rpcpass=bbl", "--wallet", "getnewaddress", "babylon"]
res = container.exec_run(cmd)
print (res.output.decode('utf-8'))

print(res.output._sock.recv(16384))
res.output._sock.send(walletpass)
print(res.output._sock.recv(16384))
res.output._sock.send(walletpass)
print(res.output._sock.recv(16384))
"""
