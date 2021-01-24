#!/usr/bin/python2
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2015 Team Kodi
#     http://kodi.tv
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
import sys
from indexer import indexer
try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser

config = ConfigParser()
if not config.read('config.cfg'):
    print("Fatal: Could not read config file.")
    sys.exit(1)


if __name__ == '__main__':
    outdir = config.get('general', 'destination')
    for target_name in os.listdir(outdir):
        target_path = os.path.join(outdir, target_name)
        if os.path.isdir(target_path):
            indexer.create_index(target_path, os.path.join(target_path, "addons.xml"))
