#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Cryptographic utility functions.

"""
:module: pyoauth.crypto.utils
:synopsis: Cryptographic utility functions.

Functions:
----------
.. autofunction:: sha1_digest
.. autofunction:: sha1_hexdigest
.. autofunction:: md5_digest
.. autofunction:: md5_hexdigest
.. autofunction:: hmac_sha1_digest
.. autofunction:: hmac_sha1_base64
.. autofunction:: generate_random_uint_string
.. autofunction:: generate_random_hex_string
.. autofunction:: bit_count
"""

import struct
import math
import binascii
import hmac
from hashlib import sha1, md5
from pyoauth.types import bytes
from pyoauth.crypto.utils.random import generate_random_bytes


def sha1_digest(*inputs):
    """
    Calculates a SHA-1 digest of a variable number of inputs.

    :param inputs:
        A variable number of inputs for which the digest will be calculated.
    :returns:
        A byte string containing the SHA-1 message digest.
    """
    md = sha1()
    for i in inputs:
        md.update(i)
    return md.digest()


def sha1_hexdigest(*inputs):
    """
    Calculates hexadecimal representation of the SHA-1 digest of a variable
    number of inputs.

    :param inputs;
        A variable number of inputs for which the digest will be calculated.
    :returns:
        Hexadecimal representation of the SHA-1 digest.
    """
    return binascii.b2a_hex(sha1_digest(*inputs))


def md5_digest(*inputs):
    """
    Calculates a MD5 digest of a variable number of inputs.

    :param inputs:
        A variable number of inputs for which the digest will be calculated.
    :returns:
        A byte string containing the MD5 message digest.
    """
    md = md5()
    for i in inputs:
        md.update(i)
    return md.digest()


def md5_hexdigest(*inputs):
    """
    Calculates hexadecimal representation of the MD5 digest of a variable
    number of inputs.

    :param inputs;
        A variable number of inputs for which the digest will be calculated.
    :returns:
        Hexadecimal representation of the MD5 digest.
    """
    return binascii.b2a_hex(md5_digest(*inputs))


def hmac_sha1_digest(key, data):
    """
    Calculates a HMAC SHA-1 digest.

    :param key:
        The key for the digest.
    :param data:
        The data for which the digest will be calculted.
    :returns:
        HMAC SHA-1 Digest.
    """
    return hmac.new(key, data, sha1).digest()


def hmac_sha1_base64(key, data):
    """
    Calculates a base64-encoded HMAC SHA-1 signature.

    :param key:
        The key for the signature.
    :param data:
        The data to be signed.
    :returns:
        Base64-encoded HMAC SHA-1 signature.
    """
    return binascii.b2a_base64(hmac_sha1_digest(key, data))[:-1]


def generate_random_uint_string(bit_strength=64, decimal=True):
    """
    Generates a random ASCII-encoded unsigned integral number in decimal
    or hexadecimal representation.

    :param bit_strength:
        Bit strength.
    :param decimal:
        ``True`` (default) if you want the decimal representation; ``False`` for
        hexadecimal.
    :returns:
        A string representation of a randomly-generated ASCII-encoded
        hexadecimal/decimal-representation unsigned integral number
        based on the bit strength specified.
    """
    if bit_strength % 8 or bit_strength <= 0:
        raise ValueError("This function expects a bit strength: got `%r`." % (bit_strength, ))
    n_bytes = bit_strength / 8
    value = binascii.b2a_hex(generate_random_bytes(n_bytes))
    if decimal:
        value = bytes(int(value, 16))
    return value


def generate_random_hex_string(length=8):
    """
    Generates a random ASCII-encoded hexadecimal string of an even length.

    :param length:
        Length of the string to be returned. Default 32.
        The length MUST be a positive even number.
    :returns:
        A string representation of a randomly-generated hexadecimal string.
    """
    if length % 2 or length <= 0:
        raise ValueError("This function expects a positive even number length: got length `%r`." % (length, ))
    return binascii.b2a_hex(generate_random_bytes(length/2))


def bit_count(n):
    """
    Determines the number of bits in a number.

    :param n:
        Number.
    :returns:
        Returns the number of bits in the number.
    """
    if n==0:
        return 0
    s = "%x" % n
    return ((len(s)-1)*4) + \
    {'0':0, '1':1, '2':2, '3':2,
     '4':3, '5':3, '6':3, '7':3,
     '8':4, '9':4, 'a':4, 'b':4,
     'c':4, 'd':4, 'e':4, 'f':4,
     }[s[0]]
    #return int(math.floor(math.log(n, 2))+1)


def byte_count(n):
    """
    Determines the number of bytes in a number.

    :param n:
        The number.
    :returns:
        The number of bytes in the number.
    """
    if n == 0:
        return 0
    bits = bit_count(n)
    return int(math.ceil(bits / 8.0))



# Improved conversion functions contributed by Barry Warsaw, after
# careful benchmarking

def long_to_bytes(n, blocksize=0):
    """
    Convert a long integer to a byte string::

        long_to_bytes(n:long, blocksize:int) : string

    :param n:
        Long value
    :param blocksize:
        If optional blocksize is given and greater than zero, pad the front of the
        byte string with binary zeros so that the length is a multiple of
        blocksize.
    :returns:
        Byte string.
    """
    # after much testing, this algorithm was deemed to be the fastest
    s = ''
    n = long(n)
    pack = struct.pack
    while n > 0:
        s = pack('>I', n & 0xffffffffL) + s
        n = n >> 32
    # strip off leading zeros
    for i in range(len(s)):
        if s[i] != '\000':
            break
    else:
        # only happens when n == 0
        s = '\000'
        i = 0
    s = s[i:]
    # add back some pad bytes.  this could be done more efficiently w.r.t. the
    # de-padding being done above, but sigh...
    if blocksize > 0 and len(s) % blocksize:
        s = (blocksize - len(s) % blocksize) * '\000' + s
    return s


def bytes_to_long(s):
    """
    Convert a byte string to a long integer::

        bytes_to_long(bytestring) : long

    This is (essentially) the inverse of long_to_bytes().

    :param bytestring:
        A byte string.
    :returns:
        Long.
    """
    acc = 0L
    unpack = struct.unpack
    length = len(s)
    if length % 4:
        extra = (4 - length % 4)
        s = '\000' * extra + s
        length = length + extra
    for i in range(0, length, 4):
        acc = (acc << 32) + unpack('>I', s[i:i+4])[0]
    return acc


# Old
#def long_to_bytes(s):
#    byte_array = bytearray_from_long(s)
#    return bytearray_to_string(byte_array)
#
#
#def bytes_to_long(s):
#    byte_array = bytearray_from_string(s)
#    return bytearray_to_long(byte_array)
