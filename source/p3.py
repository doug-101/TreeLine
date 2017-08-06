#!/usr/bin/env python3

# Simple p3 encryption "algorithm": it's just SHA used as a stream
# cipher in output feedback mode.  

# Author: Paul Rubin, Fort GNOX Cryptography, <phr-crypto at nightsong.com>.
# Algorithmic advice from David Wagner, Richard Parker, Bryan
# Olson, and Paul Crowley on sci.crypt is gratefully acknowledged.

# Copyright 2002,2003 by Paul Rubin
# Copying license: same as Python 2.3 license

# Please include this revision number in any bug reports: $Revision: 1.2 $.

# Modified by Doug Bell to be compatible with Python 3

from array import array
from time import time
import struct
import hashlib
shaHash = hashlib.sha1

class CryptError(Exception): pass
def _hash(text): return shaHash(text).digest()

_ivlen = 16
_maclen = 8
_state = _hash(repr(time()).encode())

# added by Doug Bell for compatibility with 64-bit systems
_arraytype = [t for t in 'LIH' if struct.calcsize(t) == 4][0]

try:
    import os
    _pid = repr(os.getpid()).encode()
except (ImportError, AttributeError):
    _pid = ''

def _expand_key(key, clen):
    blocks = (clen+19)//20
    xkey=[]
    seed=key
    for i in range(blocks):
        seed=shaHash(key+seed).digest()
        xkey.append(seed)
    j = b''.join(xkey)
    return array(_arraytype, j)

def p3_encrypt(plain,key):
    global _state
    H = _hash

    # change _state BEFORE using it to compute nonce, in case there's
    # a thread switch between computing the nonce and folding it into
    # the state.  This way if two threads compute a nonce from the
    # same data, they won't both get the same nonce.  (There's still
    # a small danger of a duplicate nonce--see below).
    _state = b'X'+_state

    # Attempt to make nlist unique for each call, so we can get a
    # unique nonce.  It might be good to include a process ID or
    # something, but I don't know if that's portable between OS's.
    # Since is based partly on both the key and plaintext, in the
    # worst case (encrypting the same plaintext with the same key in
    # two separate Python instances at the same time), you might get
    # identical ciphertexts for the identical plaintexts, which would
    # be a security failure in some applications.  Be careful.
    nlist = [repr(time()).encode(), _pid, _state,
             repr(len(plain)).encode(),plain, key]
    nonce = H(b','.join(nlist))[:_ivlen]
    _state = H(b'update2'+_state+nonce)
    k_enc, k_auth = H(b'enc'+key+nonce), H(b'auth'+key+nonce)
    n=len(plain)                        # cipher size not counting IV

    stream = array(_arraytype, plain+b'0000'[n&3:]) # pad to fill 32-bit words
    xkey = _expand_key(k_enc, n+4)
    for i in range(len(stream)):
        stream[i] = stream[i] ^ xkey[i]
    ct = nonce + stream.tostring()[:n]
    auth = _hmac(ct, k_auth)
    return ct + auth[:_maclen]

def p3_decrypt(cipher,key):
    H = _hash
    n=len(cipher)-_ivlen-_maclen        # length of ciphertext
    if n < 0:
        raise CryptError("invalid ciphertext")
    nonce,stream,auth = \
      cipher[:_ivlen], cipher[_ivlen:-_maclen]+b'0000'[n&3:],cipher[-_maclen:]
    k_enc, k_auth = H(b'enc'+key+nonce), H(b'auth'+key+nonce)
    vauth = _hmac (cipher[:-_maclen], k_auth)[:_maclen]
    if auth != vauth:
        raise CryptError("invalid key or ciphertext")

    stream = array(_arraytype, stream)
    xkey = _expand_key (k_enc, n+4)
    for i in range (len(stream)):
        stream[i] = stream[i] ^ xkey[i]
    plain = stream.tostring()[:n]
    return plain

# RFC 2104 HMAC message authentication code
# This implementation is faster than Python 2.2's hmac.py, and also works in
# old Python versions (at least as old as 1.5.2).
def _hmac_setup():
    global _ipad, _opad, _itrans, _otrans
    _itrans = array('B',[0]*256)
    _otrans = array('B',[0]*256)    
    for i in range(256):
        _itrans[i] = i ^ 0x36
        _otrans[i] = i ^ 0x5c
    _itrans = _itrans.tostring()
    _otrans = _otrans.tostring()

    _ipad = b'\x36'*64
    _opad = b'\x5c'*64

def _hmac(msg, key):
    if len(key)>64:
        key=shaHash(key).digest()
    ki = (key.translate(_itrans)+_ipad)[:64] # inner
    ko = (key.translate(_otrans)+_opad)[:64] # outer
    return shaHash(ko+shaHash(ki+msg).digest()).digest()

#
# benchmark and unit test
#

def _time_p3(n=1000,len=20):
    plain="a"*len
    t=time()
    for i in range(n):
        p3_encrypt(plain,b"abcdefgh")
    dt=time()-t
    print("plain p3:", n,len,dt,"sec =",n*len//dt,"bytes/sec")

def _speed():
    _time_p3(len=5)
    _time_p3()
    _time_p3(len=200)
    _time_p3(len=2000,n=100)

def _test():
    e=p3_encrypt
    d=p3_decrypt

    plain=b"test plaintext"
    key = b"test key"
    c1 = e(plain,key)
    c2 = e(plain,key)
    assert c1!=c2
    assert d(c2,key)==plain
    assert d(c1,key)==plain
    c3 = c2[:20]+chr(1+c2[20]).encode()+c2[21:] # change one ciphertext char

    try:
        print(d(c3,key))         # should throw exception
        print("auth verification failure")
    except CryptError:
        pass

    try:
        print(d(c2,b'wrong key'))        # should throw exception
        print("test failure")
    except CryptError:
        pass

_hmac_setup()
# _test()
# _speed()                                # uncomment to run speed test
