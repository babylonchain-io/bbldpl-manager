import os
import sys
import json
import time

from bbldpl_manager.container import ContainerManager
from collections import defaultdict

class BbldplManager:
    WALLET_TIMEOUT = 1800
    PROC_MIN_WAIT = 60

    def __init__(self, image_name, config_file, storage_file):
        self.config_file = os.path.abspath(config_file)
        self.storage_file = os.path.abspath(storage_file)
        self.image_name = image_name

        self.node_config = self._read_config(self.config_file)
        self.storage_config = self._read_json(self.storage_file)

        self.container_manager = ContainerManager(self.storage_config)

    def deploy(self):
        """
        For each node:
        1. Check whether it already runs, if yes, throw an error
        2. If not running create a container for it
          - create mapping of ports from host to container (via an assignment algorithm)
        3. Run the container
        4. Generate a wallet
        5. Start bbld and btcwallet
        6. Unlock wallet
        7. Generate all accounts and one address for them
        8. Restart the btcd daemon with a mining address and its connections
        """
        print("Creating a network {}...".format(self.node_config["network"]["name"]))
        self.container_manager.create_network(self.node_config["network"]["name"])

        print ("Deploying node(s)...")
        for node_name, node_info in self.node_config["nodes"].items():
            if self.container_manager.container_exists(node_name):
                print("Node {} is already running. Will not re-deploy.".format(node_name))
                continue

            ip_mapping = self._get_ip_mapping(node_info)
            print("{}: Creating container...".format(node_name))
            self.container_manager.create_container(self.image_name, node_name, self.node_config["network"]["name"], ip_mapping)

            print("{}: Generating wallet...".format(node_name))
            self.container_manager.generate_wallet(node_name, node_info["user"], node_info["pass"], node_info["walletpass"])

            print("{}: Starting bbld daemon...".format(node_name))
            self.container_manager.start_bbld_daemon(node_name, node_info["user"],
                    node_info["pass"], simnet=self.node_config["simnet"])

            print("{}: Wait for bbld daemon to come up...".format(node_name))
            time.sleep(self.PROC_MIN_WAIT)

            print("{}: Starting btcwallet daemon...".format(node_name))
            self.container_manager.start_btcwallet_daemon(node_name, node_info["user"],
                    node_info["pass"], simnet=self.node_config["simnet"])
            print("{}: Wait for btcwallet daemon to come up...".format(node_name))
            time.sleep(self.PROC_MIN_WAIT)

            print("{}: Unlocking wallet...".format(node_name))
            self.container_manager.unlock_wallet(node_name,
                    node_info["user"], node_info["pass"],
                    node_info["walletpass"], self.WALLET_TIMEOUT, simnet=self.node_config["simnet"])
            print("{}: Creating accounts...".format(node_name))
            # "default" is an already existing account name, so generate an address for it as well
            for account in node_info["accounts"] + ["default"]:
                if not self.container_manager.account_exists(node_name, node_info["user"],
                        node_info["pass"], account, simnet=self.node_config["simnet"]):
                    self.container_manager.add_account(node_name, node_info["user"], node_info["pass"], account, simnet=self.node_config["simnet"])

                address = self.container_manager.generate_address(node_name, node_info["user"],
                        node_info["pass"], account, simnet=self.node_config["simnet"])
                print("\t\t{} assigned address {}".format(account, address))


        print("Connecting nodes...")
        connections_per_node = self._get_connections_per_node()
        for node_name, node_info in self.node_config["nodes"].items():
            print("{}: Restarting bbld daemon...".format(node_name))
            self.container_manager.kill_bbld_daemon(node_name)
            self.container_manager.start_bbld_daemon(node_name,
                    node_info["user"], node_info["pass"],
                    mining_address=self.container_manager.get_first_address(node_name,
                            node_info["user"], node_info["pass"],
                            node_info["miningaccount"], simnet=self.node_config["simnet"]),
                    connections=connections_per_node[node_name],
                    simnet=self.node_config["simnet"])
        print("Wait for bbld nodes to restart".format(node_name))
        time.sleep(self.PROC_MIN_WAIT * 2)

        print("Starting mining...")
        for node_name, node_info in self.node_config["nodes"].items():
            print("{}: Starting Mining...".format(node_name))
            self.container_manager.start_mining(node_name,
                    node_info["user"], node_info["pass"],
                    simnet=self.node_config["simnet"])

        print("Done!")

    def destroy(self):
        """
        Iterates through each node and destroys its corresponding container.
        """
        print("Destroying node(s)...")
        for node_name, node_info in self.node_config["nodes"].items():
            if not self.container_manager.container_exists(node_name):
                print("Node {} is not running.".format(node_name))
                continue

            print("{}: Destroying...".format(node_name))
            self.container_manager.destroy_container(node_name)

        print("Destroying network...")
        self.container_manager.destroy_network()

        self.flush_storage()
        print("Done")

    def flush_storage(self):
        """
        Dumps the storage on the specified storage file.
        """
        with open(self.storage_file, "w+") as f:
            f.write(json.dumps(self.container_manager.get_storage()))

    ########### Internal Methods ###########

    def _get_ip_mapping(self, info):
        """
        `info` corresponds to a node configuration object.
        This method returns a mapping between the container port specified on
        the configuration (typically 18555) and a user defined port on the host.
        The communication happens via the TCP protocol.
        """
        return {
            info["port"]+"/tcp": info["hostport"]
        }

    def _get_connections_per_node(self):
        """
        Iterates through the connections specified on the configuration file
        and creates an adjacency list with node names being the keys and
        values being the connected node name and the specified port.
        Since we have created our own network and have given nodes specific
        names, we do not need to assign IP addresses, but only use the node names.
        """
        connections_per_node = defaultdict(list)
        for node1, node2 in self.node_config["connections"]:
            connections_per_node[node1].append(node2 + ":" + self.node_config["nodes"][node2]["port"])
            connections_per_node[node2].append(node1 + ":" + self.node_config["nodes"][node1]["port"])
        return connections_per_node

    def _read_config(self, config_file):
        if not os.path.exists(config_file):
            print("Configuration file {} does not exist".format(config_file))
            sys.exit(1)
        return self._read_json(config_file)

    def _read_json(self, filename):
        if not os.path.exists(filename):
            return {}

        with open(filename, "r") as f:
            return json.load(f)
