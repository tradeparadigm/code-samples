#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# Created By: Steven (steven@ribbon.finance)
# Created Date: 04/04/2022
# version ='0.01'
# ---------------------------------------------------------------------------
''' Abstract class for contract factory '''
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
from web3 import Web3
import json

# ---------------------------------------------------------------------------
# Contract Factory
# ---------------------------------------------------------------------------
class ContractFactory:
  '''
  Object to create connection to a contract

  Args:
      rpc (str): Json RPC address to connect
      address (str): Contract address
      abi (dict): Contract ABI location

  Attributes:
      address (str): Contract address
      abi (dict): Contract ABI
      w3 (object): RPC connection instance
      contract (object): Contract instance
  '''
  def __init__(self, rpc: str, address: str, abi: dict) -> None:
    self.address = address
    self.abi = abi
    self.w3 = Web3(Web3.HTTPProvider(rpc))

    if not self.w3.isConnected():
      raise ValueError('RPC connection error')

    with open(self.abi) as f:
      self.abi = json.load(f)

    self.contract = self.w3.eth.contract(self.address, abi=self.abi)