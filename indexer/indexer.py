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
import re
import gzip
import logging
import zipfile
from lxml import etree as ET
from xml.dom import minidom
from distutils.version import LooseVersion

#logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)
#logging.basicConfig(level=logging.WARN)

def split_version(path):
    result = os.path.splitext(os.path.basename(path))
    # extract name and version from file name
    # expexted format: addontype.addonname-version.zip
    # where version = a.b[.c][.d][.e][.f][+~tag]
    # e.g. script.module.idna-2.8.zip, script.module.idna-2.8.1.zip, ..., script.module.idna-2.8.1.2.3.4.zip
    #      script.module.idna-2.8.10+git010cab3.zip
    m = re.match("([\w\.]+.*)-(\d+\.\d+(\.\d+){0,4}([+~\w]+)?)", result[0])
    if m:
        return m.groups()[0:2]
    else:
        return None, None



def find_archives(repo_dir):
    for addon_id in os.listdir(repo_dir):
        logging.debug("find_archives repo_dir: {} addon_id {}".format(repo_dir, addon_id))
        if os.path.isdir(os.path.join(repo_dir, addon_id)):
            zips = [os.path.join(repo_dir, addon_id, name)
                    for name in os.listdir(os.path.join(repo_dir, addon_id))
                    if os.path.splitext(name)[1] == '.zip' and '-' in name and split_version(name) != (None, None)]
            if len(zips) > 0:
                logging.debug("find_archives found zips for addon_id {}: {}".format(addon_id, zips))
                zips.sort(key=lambda _: LooseVersion(split_version(_)[1]), reverse=True)
                yield zips[0]


def create_index(repo_dir, dest, prettify=False):
    parser = ET.XMLParser(remove_blank_text=True)
    addons = ET.Element('addons')

    archives = list(find_archives(repo_dir))
    archives.sort(key=lambda _: os.stat(_).st_mtime, reverse=True)

    for archive in archives:
        addon_id, version = split_version(archive)
        if (addon_id is None or version is None):
            logging.exception("Failed to parse addon version from '%s'. Skipping" % archive)
            continue

        with zipfile.ZipFile(archive, 'r') as zf:
            tree = None

            logging.info("parsing archive {}: addon_id: {}, version: {}".format(archive, addon_id, version))
            try:
                tree = ET.fromstring(zf.read(os.path.join(addon_id, 'addon.xml')), parser)
            except (ET.ParseError, KeyError, IndexError) as e:
                logging.exception("Failed to read addon info from '%s'. Skipping" % archive)
                continue

            metadata_elem = tree.find("./extension[@point='kodi.addon.metadata']")
            if metadata_elem is None:
                metadata_elem = tree.find("./extension[@point='xbmc.addon.metadata']")

            # for backwards compatibility with add-ons that do not use the assets element
            if metadata_elem.find('./assets') is None:
                no_things = ['icon.png', 'fanart.jpg', 'changelog.txt']
                for no_thing in no_things:
                    if os.path.join(addon_id, no_thing) not in zf.namelist():
                        elem = ET.SubElement(metadata_elem, 'no' + os.path.splitext(no_thing)[0])
                        elem.text = "true"

            elem = ET.SubElement(metadata_elem, 'size')
            elem.text = str(os.path.getsize(archive))

            elem = ET.SubElement(metadata_elem, 'path')
            elem.text = str(os.path.relpath(archive, repo_dir))

            addons.append(tree)

    xml = ET.tostring(addons, encoding='utf-8', xml_declaration=True)
    if prettify:
        xml = minidom.parseString(xml).toprettyxml(encoding='utf-8', indent="  ")

    with open(dest, 'wb') as f:
        f.write(xml)

    with gzip.GzipFile(dest + ".gz", 'wb', compresslevel=9, mtime=0) as f:
        f.write(xml)
