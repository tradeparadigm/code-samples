#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#----------------------------------------------------------------------------
# Created By: Steven (steven@ribbon.finance)
# Created Date: 04/04/2022
# version ='0.01'
# ---------------------------------------------------------------------------
''' Module to encode message '''
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
from web3 import Web3
import re
from utils import *

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DOMAIN_FIELD_NAMES = [
  'name', 
  'version', 
  'chainId', 
  'verifyingContract', 
  'salt'
]
DOMAIN_FIELD_TYPES = {
    'name': 'string',
    'version': 'string',
    'chainId': 'uint256',
    'verifyingContract': 'address',
    'salt': 'bytes32'
}

HEX_TRUE = hexZeroPad(Web3.toHex(1), 32)
HEX_FALSE = hexZeroPad(Web3.toHex(0), 32)

# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
def uintEncoder(type: str) -> object:
  '''
  Encoder for uint types

  Args:
      type (str): Data type in string

  Returns:
      encoder (object): Uint encoder
  '''
  match = re.findall('^(u?)int(\d*)$', type).pop()
  signed = (match[1] == '')
  width = int(match[2]) if len(match) == 3 else 256

  if (
    width % 8 != 0
    or width > 256
    or (len(match) == 3 and match[2] != str(width))
  ):
    raise ValueError(f'Invalid numeric width: {type}')
  
  boundsUpper = 2**(width-1) - 1 if signed else 2**(width) - 1
  boundsLower = (boundsUpper + 1)*(-1)
  return lambda value: \
    hexZeroPad(Web3.toHex(int(value)), 32) \
      if int(value) < boundsUpper and int(value) > boundsLower \
      else ValueError('Value out of bounds')

def bytesEncoder(type: str) -> object:
  '''
  Encoder for bytes types

  Args:
      type (str): Data type in string

  Returns:
      encoder (object): Bytes encoder
  '''
  match = re.findall('^bytes(\d+)$', type).pop()
  width = int(match[1])

  if width == 0 or width > 32 or match[1] != str(width):
    raise ValueError(f'Invalid bytes width: {type}')

  return lambda value: \
    hexPadRight(value) if len(value) == width \
    else ValueError('Invalid bytes length')

def getBaseEncoder(type: str) -> object:
  '''
  Get the encoder for base types

  Args:
      type (str): Data type in string

  Returns:
      encoder (object): Encoder
  '''
  if re.match('^(u?)int(\d*)$', type):
    return uintEncoder(type)
  elif re.match('^bytes(\d+)$', type):
    return bytesEncoder(type)
  elif type == 'address':
    return lambda value: hexZeroPad(getAddress(value), 32)
  elif type == 'bool':
    return lambda value: HEX_TRUE if value else HEX_FALSE
  elif type == 'bytes':
    return lambda value: Web3.keccak(text=value)
  elif type == 'string':
    return lambda value: id(value)
  else:
    return None

class TypedDataEncoder:
  '''
  Object to encode typed data

  Args:
      types (dict): Dictionary of data types

  Attributes:
      types (dict): Instance of signer to generate signature
      _encoderCache (dict): Dictionary container to cache encoder
      _types (dict): Dictionary container to cache struct names
      links (dict): Dictionary container to store links between structs
      parents (dict): Dictionary container to store parent of structs
      subtypes (dict): Dictionary container to check circular reference
      primaryType (dict): Primary type to encode
  '''
  def __init__(self, types: dict) -> None:
    self.types = types
    self._encoderCache = {}
    self._types = {}
    self.links = {}
    self.parents = {}
    self.subtypes = {}

    for type in types.keys():
      self.links[type] = {}
      self.parents[type] = []
      self.subtypes[type] = {}

    for name in types.keys():
      uniqueNames = {}

      for field in types[name]:
        fieldName = field['name']
        
        if fieldName in uniqueNames.keys():
          raise ValueError(f'Duplicate variable name {fieldName} in {name}')

        uniqueNames[fieldName] = True

        baseType = re.sub('\[[^()]*\]', '', field['type'])

        if baseType == name:
          raise ValueError(f'Circular type reference: {baseType}')

        encoder = getBaseEncoder(baseType)

        if encoder:
          continue
        
        self.parents[baseType].push(name)
        self.links[name][baseType] = True

    primaryTypes = [type for type in self.parents.keys() 
      if len(self.parents[type]) == 0]

    if len(primaryTypes) == 0:
      raise ValueError('Missing primary type')
    elif len(primaryTypes) > 1:
      raise ValueError('Ambiguous primary types or unused types')

    self.primaryType = primaryTypes[0]

    def checkCircular(type: str, found: dict):
      if type in found.keys():
        raise ValueError(f'Circular type reference to {type}')
      
      found[type] = True

      for child in self.links[type].keys():
        if child not in self.parents.keys():
          checkCircular(child, found)

          for subtype in found.keys():
            self.subtypes[subtype][child] = True
      
      del found[type]
    
    checkCircular(self.primaryType, {})

    for name in self.subtypes.keys():
      st = list(self.subtypes[name].keys())
      st.sort()
      self._types[name] = encodeType(name, types[name]) \
        + ''.join([encodeType(t, types[t]) for t in st])

  def _getEncoder(self, type: str) -> object:
    '''
    Get the encoder for a given type

    Args:
        type (str): Data type in string

    Returns:
        encoder (object): Encoder
    '''
    encoder = getBaseEncoder(type)
    if encoder is not None:
      return encoder

    match = re.findall('\[[^()]*\]', type)
    if len(match) > 0:
      match = type[:-1].split('[')
      subtype = match[0]
      subEncoder = self.getEncoder(subtype)
      length = 0 if len(match) == 1 else int(match[1])
      print(length)
      return lambda values: \
        Web3.keccak(
          text=hexConcat(
            [Web3.keccak(text=subEncoder(value)) for value in values] \
              if subtype in self._types.keys() \
              else [subEncoder(value) for value in values]
          )
        ).hex() \
          if length >= 0 and len(values) == length \
          else ValueError('Array length mismatched')

    fields = self.types[type]
    if fields is not None:
      encodedType = id(self._types[type])
      return lambda value: hexConcat(
        [encodedType] + [self.getEncoder(field['type'])(value[field['name']]) 
          if field['type'] not in self._types.keys() \
          else Web3.keccak(
            text=self.getEncoder(field['type'])(value[field['name']])
          ).hex() for field in fields]
        )

  def getEncoder(self, type: str) -> object:
    '''
    Get the base encoder for a given type and store it in cache

    Args:
        type (str): Data type in string

    Returns:
        encoder (object): Encoder
    '''
    if type in self._encoderCache.keys():
      return self._encoderCache[type]
    else:
      encoder = self._getEncoder(type)
    
    return encoder

  def encodeData(self, type: str, value: dict) -> str:
    '''
    Encode the value of a given type

    Args:
        type (str): Data type in string
        value (dict): Values corresponding to the type

    Returns:
        data (str): Encoded data
    '''
    return self.getEncoder(type)(value)

  def hashStruct(self, name: str, value: dict) -> str:
    '''
    Generate the hash of encoded data given a type and value

    Args:
        name (str): Data type in string
        value (dict): Values corresponding to the type

    Returns:
        hash (str): Hash of encoded data
    '''
    return Web3.keccak(hexstr=self.encodeData(name, value)).hex()

  def hash(self, value: dict) -> str:
    '''
    Generate the hash of encoded data for the primary type given a value

    Args:
        value (dict): Values corresponding to the primary type

    Returns:
        hash (str): Hash of encoded data
    '''
    return self.hashStruct(self.primaryType, value)

  @staticmethod
  def _from(types: dict) -> object:
    '''
    Create a new instance of TypedDataEncoder for a given types

    Args:
        types (dict): Dictionary of data types

    Returns:
        TypedDataEncoder (str): A new instance of TypedDataEncoder
    '''
    return TypedDataEncoder(types)

  @staticmethod
  def _hashStruct(name: str, types: dict, value: dict) -> str:
    '''
    Generate the hash of encoded data given a name, types and value

    Args:
        name(str): Data type in string
        types (dict): Dictionary of data types
        value (dict): Values corresponding to the type

    Returns:
        hash (str): Hash of encoded data
    '''
    return TypedDataEncoder._from(types).hashStruct(name, value)

  @staticmethod
  def hashDomain(domain: dict) -> str:
    '''
    Encode the domain dictionary

    Args:
        domain (dict): Domain values in dictionary

    Returns:
        hash (str): Hash of encoded domain data
    '''
    domainFields = []
    for name in domain.keys():
      if name not in DOMAIN_FIELD_NAMES:
        raise ValueError('Invalid domain key')
      
      domainFields.append({'name': name, 'type': DOMAIN_FIELD_TYPES[name]})
    
    domainFields.sort(key=lambda x: DOMAIN_FIELD_NAMES.index(x['name']))

    return TypedDataEncoder._hashStruct(
      'EIP712Domain', 
      { 'EIP712Domain': domainFields }, 
      domain
    )

  @staticmethod
  def encode(domain: dict, types: dict, value: dict) -> str:
    '''
    Encode a message

    Args:
        domain (dict): Domain values in dictionary
        types (dict): Dictionary of data types
        value (dict): Values corresponding to the types

    Returns:
        data (str): Encoded message
    '''
    return hexConcat([
      '0x1901',
      TypedDataEncoder.hashDomain(domain),
      TypedDataEncoder._from(types).hash(value)
    ])

  @staticmethod
  def _hash(domain: dict, types: dict, value: dict) -> str:
    '''
    Generate a hash of a message following the EIP712 convention:
    https://eips.ethereum.org/EIPS/eip-712

    Args:
        domain (dict): Domain values in dictionary
        types (dict): Dictionary of data types
        value (dict): Values corresponding to the types

    Returns:
        hash (str): Hash of message
    '''
    return Web3.keccak(
      hexstr=TypedDataEncoder.encode(domain, types, value)
    ).hex()
