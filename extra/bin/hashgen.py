#!/bin/env python3
import crypt
import getpass

password = getpass.getpass("\nWhat password would you like to hash/salt?\n(NOTE: will NOT echo back!)\n")
salt = crypt.mksalt(crypt.METHOD_SHA512)
salthash = crypt.crypt(password, salt)
print("\nYour salted hash is:\n\t{0}\n".format(salthash))
