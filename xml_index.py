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
import gzip
import zipfile
from lxml import etree as ET
from xml.dom import minidom
from argparse import ArgumentParser
from distutils.version import LooseVersion


def split_version(path):
    return os.path.splitext(os.path.basename(path))[0].rsplit('-', 1)


def find_archives(repo_dir):
    for addon_id in os.listdir(repo_dir):
        if os.path.isdir(os.path.join(repo_dir, addon_id)):
            zips = [os.path.join(repo_dir, addon_id, name)
                    for name in os.listdir(os.path.join(repo_dir, addon_id))
                    if os.path.splitext(name)[1] == '.zip' and '-' in name]
            if len(zips) > 0:
                zips.sort(key=lambda _: LooseVersion(split_version(_)[1]), reverse=True)
                yield zips[0]


def create_index(repo_dir, dest, prettify=False):
    parser = ET.XMLParser(remove_blank_text=True)
    addons = ET.Element('addons')

    archives = list(find_archives(repo_dir))
    archives.sort(key=lambda _: os.stat(_).st_mtime, reverse=True)

    for archive in archives:
        addon_id, version = split_version(archive)
        with zipfile.ZipFile(archive, 'r') as zf:
            addonxml = zf.read(os.path.join(addon_id, 'addon.xml'))
            tree = ET.fromstring(addonxml, parser)

            metadata_elem = tree.find("./extension[@point='kodi.addon.metadata']")
            if metadata_elem is None:
                metadata_elem = tree.find("./extension[@point='xbmc.addon.metadata']")

            no_things = ['icon.png', 'fanart.jpg', 'changelog.txt']
            for no_thing in no_things:
                if os.path.join(addon_id, no_thing) not in zf.namelist():
                    elem = ET.SubElement(metadata_elem, 'no' + os.path.splitext(no_thing)[0])
                    elem.text = "true"
            addons.append(tree)

    xml = ET.tostring(addons, encoding='utf-8', xml_declaration=True)
    if prettify:
        xml = minidom.parseString(xml).toprettyxml(encoding='utf-8', indent="  ")

    with open(dest, 'wb') as f:
        f.write(xml)

    with gzip.open(dest + ".gz", 'wb', 9) as f:
        f.write(xml)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('-i', '--input', dest='input', required=True, help="Path to the generated repository")
    parser.add_argument('-o', '--output', dest='output', required=True)
    parser.add_argument('-p', '--prettify', dest='prettify', action='store_true', default=False)
    args = parser.parse_args()
    create_index(args.input, args.output, prettify=args.prettify)
