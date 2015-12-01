#!/usr/bin/python
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
from xml_index import create_index
from updaterepo import outdir


if __name__ == '__main__':
    for target_name in os.listdir(outdir):
        target_path = os.path.join(outdir, target_name)
        if os.path.isdir(target_path):
            create_index(target_path, os.path.join(target_path, "addons.xml"))
