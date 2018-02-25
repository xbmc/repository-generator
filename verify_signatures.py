#!/usr/bin/python
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
import sys
from signing import find_artifacts, verify_signatures


if __name__ == '__main__':
    path = sys.argv[1]
    with open('public.pem') as f:
        key = f.read()

    files = find_artifacts(path)
    verify_signatures(files, key)
    verify_signatures([os.path.join(path, 'addons.xml.gz')], key)
