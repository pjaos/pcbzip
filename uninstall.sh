#!/bin/sh
set -e

#Uninstall if only installed for current user
#python3 -m pip uninstall pcbzip

#Uninstall if installed for all users
sudo python3 -m pip uninstall pcbzip

