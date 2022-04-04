#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# Created By: Steven (steven@ribbon.finance)
# Created Date: 04/04/2022
# version ='0.01'
# ---------------------------------------------------------------------------
''' Module to generate signature to bid '''
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import eth_keys
from encode import TypedDataEncoder

# ---------------------------------------------------------------------------
# Signature Generator
# ---------------------------------------------------------------------------
class SignatureGenerator:
  '''
  Object to generate bid signature

  Args:
      privateKey (str): Private key of the user in hex format with 0x prefix

  Attributes:
      signer (object): Instance of signer to generate signature
  '''
  def __init__(self, privateKey: str) -> None:
    self.signer = eth_keys.keys.PrivateKey(bytes.fromhex(privateKey[2:]))

  def signMessage(self, messageHash: str) -> dict:
    '''Sign a hash message using the signer object

    Args:
        messageHash (str): Message to signed in hex format with 0x prefix

    Returns:
        signature (dict): Signature split into v, r, s components
    '''
    signature = self.signer.sign_msg_hash(bytes.fromhex(messageHash[2:]))

    return {
      'v': signature.v + 27,
      'r': hex(signature.r),
      's': hex(signature.s)
    }

  def _signTypedDataV4(self, domain: dict, types: dict, value: dict) -> str:
    '''Sign a hash of typed data V4 which follows EIP712 convention:
    https://eips.ethereum.org/EIPS/eip-712
    
    Args:
        domain (dict): Dictionary containing domain parameters including
          name, version, chainId, verifyingContract and salt (optional)
        types (dict): Dictionary of types and their fields
        value (dict): Dictionary of values for each field in types

    Returns:
        signature (dict): Signature split into v, r, s components
    '''
    return self.signMessage(TypedDataEncoder._hash(domain, types, value))

  def sign(self, domain: dict, types: dict, bid: dict) -> dict:
    '''Sign a bid using _signTypedDataV4
    
    Args:
        domain (dict): Dictionary containing domain parameters including
          name, version, chainId, verifyingContract and salt (optional)
        types (dict): Dictionary of types and their fields
        bid (dict): Dicionary of bid specification

    Returns:
        signedBid (dict): Bid combined with the generated signature
    '''
    signature = self._signTypedDataV4(domain, types, bid)

    return {
      'swapId': bid['swapId'],
      'nonce': bid['nonce'],
      'signerWallet': bid['signerWallet'],
      'sellAmount': bid['sellAmount'],
      'buyAmount': bid['buyAmount'],
      'referrer': bid['referrer'],
      'v': signature['v'],
      'r': signature['r'],
      's': signature['s']
    }

