# Babylon Deployment Manager

This package implements an interface for deploying and managing
multiple Babylon nodes deployed as Docker containers on a single machine.

## Installation

First, you need to create a Docker image corresponding to a Babylon node. To do
that, follow the instructions on the [Babylon Docker](https://github.com/babylonchain-io/bbld-docker)
deployment repository.

After that,

```bash
>>> python3 setup.py install
```

## Configuration

The Babylon deployment manager works based on a configuration file containing
details about each instance of a Babylon node that it manages. This
configuration file looks like this (a sample can be found on
`config/config.json.example`):

```json
{
    "nodes": {
        "nodeName1": {
            "user": "bbl1",
            "pass": "bbl2",
            "port": "18555",
            "rpcport": "18556",
            "walletpass": "supersecret",
            "accounts": ["account1", "account2"],
            "miningaccount": "account1",
            "hostport": "18888"
        },
        "nodeName2": {
            "user": "bbl1",
            "pass": "bbl2",
            "port": "18555",
            "rpcport": "18556",
            "walletpass": "supersecret2",
            "accounts": ["account1", "account2"],
            "miningaccount": "account2",
            "hostport": "18889"
        }
    },
    "connections": {
        "internal": [
            ["nodeName1", "nodeName2"]
        ],
        "external": [
            ["nodeName1", "192.168.1.1:8888"]
        ]
    },
    "network": {
        "name": "babylon-network"
    },
    "simnet": "true"
}
```

The execution of the Babylon deployment manager leads to the generation of a
storage file, used to perform future operations. These storage files look like
this (a sample can be found on `config/storage.json.example`):

```json
{
  "network": "networkID",
  "nodeName1": {
    "containerID": "containerID",
    "accounts": {
      "account1": {
        "addresses": [
          "accountaddress"
        ]
      },
      "account2": {
        "addresses": [
          "accountaddress"
        ]
      },
      "default": {
        "addresses": [
          "accountaddress"
        ]
      }
    },
    "wallet": {
      "seed": ""
    }
  },
  "nodeName2": {
    "containerID": "containerID",
    "accounts": {
      "account1": {
        "addresses": [
          "accountaddress"
        ]
      },
      "account2": {
        "addresses": [
          "accountaddress"
        ]
      },
      "default": {
        "addresses": [
          "accountaddress"
        ]
      }
    },
    "wallet": {
      "seed": ""
    }
  }
}
```

## Usage

```
>>> bbldpl-manager -h
usage: bbldpl-manager [-h] [--config CONFIG] [--storage STORAGE] [--image IMAGE] {deploy,destroy}

positional arguments:
  {deploy,destroy}   Command to be executed.

optional arguments:
  -h, --help         show this help message and exit
  --config CONFIG    Path to configuration file
  --storage STORAGE  Path to storage file
  --image IMAGE      Name of the Docker image to be used
```
