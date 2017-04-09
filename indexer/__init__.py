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

from argparse import ArgumentParser
from .indexer import create_index

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-i', '--input', dest='input', required=True, help="Path to the generated repository")
    parser.add_argument('-o', '--output', dest='output', required=True)
    parser.add_argument('-p', '--prettify', dest='prettify', action='store_true', default=False)
    args = parser.parse_args()
    create_index(args.input, args.output, prettify=args.prettify)
