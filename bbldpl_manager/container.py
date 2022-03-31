import docker
import json

from docker.utils.socket import read

class ContainerManager:
    CONTAINER_PLATFORM="linux/amd64"

    def __init__(self, storage_config):
        self.storage_config = storage_config
        self.client = docker.from_env()

    def container_exists(self, node_name):
        return self._get_container(node_name) != None

    def create_container(self, image_name, node_name, net_name, ip_mapping):
        if self._get_container(node_name):
            raise ContainerNameExistsError()

        container = self.client.containers.run(image_name,
                platform=self.CONTAINER_PLATFORM, ports=ip_mapping,
                network=net_name, name=node_name, tty=True, detach=True)
        container.start()
        self.storage_config[node_name] = self._create_empty_storage_object()
        self.storage_config[node_name]["containerID"] = container.id

    def destroy_container(self, node_name):
        container = self._get_container(node_name)
        if not container:
            raise ContainerNameDoesNotExistError()

        container.stop()
        container.remove()
        del self.storage_config[node_name]

    def start_bbld_daemon(self, node_name, rpcuser, rpcpass, rpcport, port,
            mining_address=None, connections=[], simnet=False):
        container = self._get_container(node_name)
        if not container:
            raise ContainerNameDoesNotExistError()

        # Construct bbld command
        bbld_cmd = ["bbld", "--rpcuser=" + rpcuser, "--rpcpass=" + rpcpass,
                "--rpclisten=0.0.0.0:" + rpcport, "--listen=0.0.0.0:" + port]
        if simnet:
            bbld_cmd += ["--simnet"]
        if mining_address:
            bbld_cmd += ["--miningaddr=" + mining_address, "--txindex"]
        for connection in connections:
            bbld_cmd += ["--connect=" + connection]

        self._execute_cmd(container, bbld_cmd, detach=True)

    def kill_bbld_daemon(self, node_name):
        container = self._get_container(node_name)
        if not container:
            raise ContainerNameDoesNotExistError()
        pid_of_bbld = self._execute_cmd(container,
                ["pidof", "-x", "bbld"]).decode('utf-8').strip()
        self._execute_cmd(container, '/bin/bash -c "kill ' + pid_of_bbld + '"')

    def start_btcwallet_daemon(self, node_name, user, passw, simnet=False):
        container = self._get_container(node_name)
        if not container:
            raise ContainerNameDoesNotExistError()

        # Construct btcwallet command
        btcwallet_cmd = ["btcwallet", "-u", user, "-P", passw]
        if simnet:
            btcwallet_cmd += ["--simnet"]

        self._execute_cmd(container, btcwallet_cmd, detach=True)

    def generate_wallet(self, node_name, user, passw, walletpass, simnet=False):
        # TODO: Does not properly retrieve the wallet generation seed
        container = self._get_container(node_name)
        if not container:
            raise ContainerNameDoesNotExistError()

        # Execute command for creation of wallet
        cmd = ["btcwallet", "-u", user, "-P", passw, "--create"]
        if simnet:
            cmd += ["--simnet"]
        answers = [walletpass, walletpass, "no", "no", "OK"]

        res = container.exec_run(cmd, tty=True, stdin=True, socket=True)
        socket = res.output

        # "Enter the private passphrase for your new wallet:"
        self._socket_wait(socket)
        socket._sock.send(bytes(walletpass, 'ascii'))
        socket._sock.send(bytes('\n', 'ascii'))

        # "Confirm passphrase:"
        self._socket_wait(socket)
        socket._sock.send(bytes(walletpass, 'ascii'))
        socket._sock.send(bytes('\n', 'ascii'))

        # "Do you want to add an additional layer of encryption
        # for public data? (n/no/y/yes) [no]:"
        self._socket_wait(socket)
        socket._sock.send(b'no\n')

        # "Do you have an existing wallet seed you want to
        # use? (n/no/y/yes) [no]:"
        self._socket_wait(socket)
        socket._sock.send(b'no\n')

        # "Once you have stored the seed in a safe and secure
        # location, enter "OK" to continue:"
        self._socket_wait(socket)
        socket._sock.send(b'OK\n')
        self._socket_wait(socket)

        # Store seed in storage file
        self.storage_config[node_name]["wallet"]["seed"] = "" # TODO

    def unlock_wallet(self, node_name, rpcuser, rpcpass, walletpass,
            timeout, simnet=False):
        container = self._get_container(node_name)
        if not container:
            raise ContainerNameDoesNotExistError()

        unlock_wallet_cmd = ["btcctl",
                "--rpcuser=" + rpcuser, "--rpcpass=" + rpcpass,
                "--wallet", "walletpassphrase", walletpass, str(timeout)]
        if simnet:
            unlock_wallet_cmd += ["--simnet"]

        self._execute_cmd(container, unlock_wallet_cmd)

    def account_exists(self, node_name, rpcuser, rpcpass, account, simnet=False):
        container = self._get_container(node_name)
        if not container:
            raise ContainerNameDoesNotExistError()

        accounts = self._get_accounts(container, node_name, rpcuser, rpcpass, simnet)

        return account in accounts

    def add_account(self, node_name, rpcuser, rpcpass, account, simnet=False):
        container = self._get_container(node_name)
        if not container:
            raise ContainerNameDoesNotExistError()

        if self.account_exists(node_name, rpcuser, rpcpass, account, simnet):
            return

        add_account_cmd = ["btcctl", "--rpcuser=" + rpcuser, "--rpcpass=" + rpcpass,
                "--wallet", "createnewaccount", account]
        if simnet:
            add_account_cmd += ["--simnet"]

        self._execute_cmd(container, add_account_cmd)
        self.storage_config[node_name]["accounts"][account] = {"addresses": []}

    def generate_address(self, node_name, rpcuser, rpcpass, account, simnet=False):
        container = self._get_container(node_name)
        if not container:
            raise ContainerNameDoesNotExistError()

        if not self.account_exists(node_name, rpcuser, rpcpass, account, simnet):
            raise ContainerAccountDoesNotExistError(
                    "Account {} does not exist".format(account))

        if not account in self.storage_config[node_name]["accounts"]:
            self.storage_config[node_name]["accounts"][account] = {
                "addresses": []
            }

        generate_addr_cmd = ["btcctl", "--rpcuser=" + rpcuser,
                "--rpcpass=" + rpcpass, "--wallet", "getnewaddress", account]
        if simnet:
            generate_addr_cmd += ["--simnet"]
        address = self._execute_cmd(container,
                generate_addr_cmd).decode('utf-8').strip()
        self.storage_config[node_name]["accounts"][account]["addresses"].append(address)
        return address

    def get_addresses(self, node_name, rpcuser, rpcpass, account, simnet=False):
        container = self._get_container(node_name)
        if not container:
            raise ContainerNameDoesNotExistError()

        if not self.account_exists(node_name, rpcuser, rpcpass, account, simnet):
            raise ContainerAccountDoesNotExistError(
                    "Account {} does not exist".format(account))

        get_address_cmd = ["btcctl", "--rpcuser=" + rpcuser, "--rpcpass=" + rpcpass,
                "--wallet", "getaddressesbyaccount", account]
        if simnet:
            get_address_cmd += ["--simnet"]

        addresses = json.loads(self._execute_cmd(container, get_address_cmd))
        return addresses

    def get_first_address(self, node_name, rpcuser, rpcpass, account, simnet=False):
        addresses = self.get_addresses(node_name, rpcuser, rpcpass, account, simnet)
        if len(addresses):
            return addresses[0]

    def create_network(self, network_name):
        network = self.client.networks.create(network_name)
        self.storage_config["network"] = network.id

    def destroy_network(self):
        if not "network" in self.storage_config:
            return
        try:
            self.client.networks.get(self.storage_config["network"]).remove()
        except docker.errors.NotFound as e:
            raise NetworkNotFoundException("Network {} does not exist".format(network_name))

        del self.storage_config["network"]

    def start_mining(self, node_name, rpcuser, rpcpass, simnet=False):
        container = self._get_container(node_name)
        if not container:
            raise ContainerNameDoesNotExistError()

        start_mining_cmd = ["btcctl", "--rpcuser=" + rpcuser,
                "--rpcpass=" + rpcpass, "--wallet", "setgenerate", "1"]
        if simnet:
            start_mining_cmd += ["--simnet"]

        self._execute_cmd(container, start_mining_cmd)

    def stop_mining(self, node_name, rpcuser, rpcpass, simnet=False):
        container = self._get_container(node_name)
        if not container:
            raise ContainerNameDoesNotExistError()

        stop_mining_cmd = ["btcctl", "--rpcuser=" + rpcuser,
                "--rpcpass=" + rpcpass, "--wallet", "setgenerate", "0"]
        if simnet:
            stop_mining_cmd += ["--simnet"]

        self._execute_cmd(container, stop_mining_cmd)

    def get_storage(self):
        return self.storage_config

    ############# Internal methods ############

    def _get_containers(self):
        return self.client.containers.list(all=True)

    def _create_empty_storage_object(self):
        return {
            "containerID": "",
            "accounts": {},
            "wallet": {"seed": ""}
        }

    def _get_container(self, node_name):
        if not node_name in self.storage_config:
            return None
        stored_container_id = self.storage_config[node_name]["containerID"]
        for container in self._get_containers():
            if container.id == stored_container_id:
                return container

        return None

    def _execute_cmd(self, container, cmd, detach=False):
        output = None
        try:
            _, output = container.exec_run(cmd, detach=detach)
        except docker.errors.APIError as e:
            raise ContainerCommandExecutionError(e)

        return output

    def _socket_wait(self, socket):
        """
        Waits for the socket to load a response. Hacky.
        """
        while 1:
            now = read(socket, 4096)
            if now == b'\r\n':
                continue
            break

    def _get_accounts(self, container, node_name, rpcuser, rpcpass, simnet):
        list_accounts_cmd = ["btcctl", "--rpcuser=" + rpcuser, "--rpcpass=" + rpcpass,
                "--wallet", "listaccounts"]
        if simnet:
            list_accounts_cmd += ["--simnet"]

        accounts = self._execute_cmd(container, list_accounts_cmd)
        return json.loads(self._execute_cmd(container, list_accounts_cmd))

#### Exception definitions
class ContainerException(Exception):
    pass

class ContainerNameExistsError(ContainerException):
    pass

class ContainerNameDoesNotExistError(ContainerException):
    pass

class ContainerAccountDoesNotExistError(ContainerException):
    pass

class ContaineWalletGenerationError(ContainerException):
    pass

class ContainerCommandExecutionError(ContainerException):
    pass

class NetworkException(Exception):
    pass

class NetworkNotFoundException(NetworkException):
    pass
