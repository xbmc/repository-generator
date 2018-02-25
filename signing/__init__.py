# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 Thomas Amland
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA256


def find_artifacts(path):
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".zip"):
                yield os.path.join(root, file)


def _hash_file(path):
    hash = SHA256.new()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if chunk == b'':
                break
            hash.update(chunk)
    return hash


def sign_artifacts(paths, key):
    key = RSA.importKey(key)
    signer = PKCS1_v1_5.new(key)
    for path in paths:
        hash = _hash_file(path)
        signature = signer.sign(hash)
        with open(path + '.sig', 'wb') as f:
            f.write(signature)


def verify_signatures(paths, key):
    key = RSA.importKey(key)
    verifier = PKCS1_v1_5.new(key)
    for path in paths:
        signature = None
        with open(path + '.sig', 'rb') as f:
            signature = f.read()
        hash = _hash_file(path)
        valid = verifier.verify(hash, signature)
        print("%s: valid: %s" % (path, valid))
