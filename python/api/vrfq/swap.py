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
from contract import ContractFactory

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_ABI_LOCATION = 'abis/Swap.json'

# ---------------------------------------------------------------------------
# Swap Contract Factory
# ---------------------------------------------------------------------------
class SwapFactory(ContractFactory):
  '''
  Object to create connection to the Swap contract

  Args:
      rpc (str): Json RPC address to connect
      address (str): Contract address
      abi (dict): Contract ABI location
  '''
  def __init__(self, rpc: str, address: str, abi: dict=DEFAULT_ABI_LOCATION):
        super().__init__(rpc, address, abi)

  def validateBid(self, bid: dict) -> str:
    '''
    Method to validate bid

    Args:
        bid (dict): Bid dictionary containing swapId, nonce, signerWallet, 
          sellAmount, buyAmount, referrer, v, r, and s

    Returns:
        response (dict): Dictionary containing number of errors (errors)
          and the corresponding error messages (messages)
    '''
    try:
      params = {
        'swapId': int(bid['swapId']),
        'nonce': int(bid['nonce']),
        'signerWallet': bid['signerWallet'],
        'sellAmount': int(bid['sellAmount']),
        'buyAmount': int(bid['buyAmount']),
        'referrer': bid['referrer'],
        'v': int(bid['v']),
        'r': bid['r'],
        's': bid['s'],
      }
    except:
      raise TypeError('Invalid bid')

    response = self.contract.functions.check(params).call()
    
    errors = response[0]
    if errors == 0:
      return {'errors': 0}
    else:
      return {
        'errors': errors,
        'messages': [Web3.toText(msg).replace('\x00', '') 
          for msg in response[1][1:errors]
        ]
      }