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

import contextlib
import os
import shutil
import tempfile
from collections import namedtuple
from xml.etree import ElementTree as ET
from packager.textures import pack_textures
import zipfile


def makedirs_ignore_errors(path):
    try:
        os.makedirs(path)
    except OSError:
        pass


@contextlib.contextmanager
def tempdir():
    directory = tempfile.mkdtemp()
    try:
        yield directory
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def delete_companion_files(path):
    for name in os.listdir(path):
        # TODO: remove after krypton
        if name.startswith("changelog-") and name.endswith(".txt"):
            continue

        if os.path.splitext(name)[1] != '.zip':
            try:
                if os.path.isdir(os.path.join(path, name)):
                    shutil.rmtree(os.path.join(path, name))
                else:
                    os.remove(os.path.join(path, name))
            except (IOError, OSError) as ex:
                logger.warning("Failed to remove companion file '%s'" % os.path.join(path, name))
                logger.exception(ex)


def meets_version_requirements(imports, min_versions):
    for addon_id, imported_version in imports:
        if addon_id in min_versions:
            if imported_version < min_versions[addon_id]:
                return False
    return True


def pack_artifact(artifact, src_dir, dst_dir):
    xml = ET.parse(os.path.join(src_dir, 'addon.xml'))
    pack_textures(xml, src_dir)

    # Copy asset files
    assets = xml.find("./extension[@point='kodi.addon.metadata']/assets")
    if assets is None:
        assets = xml.find("./extension[@point='xbmc.addon.metadata']/assets")

    if assets is not None:
        for item in assets:
            if item.text:
                makedirs_ignore_errors(os.path.join(dst_dir, os.path.dirname(item.text)))
                shutil.copyfile(os.path.join(src_dir, item.text), os.path.join(dst_dir, item.text))

    else:  # for backwards compatibility with add-ons that do not use the assets element
        if os.path.exists(os.path.join(src_dir, "icon.png")):
            shutil.copyfile(os.path.join(src_dir, "icon.png"), os.path.join(dst_dir, "icon.png"))

        if os.path.exists(os.path.join(src_dir, "fanart.jpg")):
            shutil.copyfile(os.path.join(src_dir, "fanart.jpg"), os.path.join(dst_dir, "fanart.jpg"))

        if os.path.exists(os.path.join(src_dir, "changelog.txt")):
            shutil.copyfile(os.path.join(src_dir, "changelog.txt"), os.path.join(dst_dir, "changelog-%s.txt" % artifact.version))

    # Write and compress files in src_dir to the final zip file
    dest_file = os.path.join(dst_dir, "%s-%s.zip" % (artifact.addon_id, artifact.version))
    with zipfile.ZipFile(dest_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(src_dir):
            for name in files:
                local_path = os.path.join(root, name)
                archive_dest = artifact.addon_id + '/' + os.path.relpath(local_path, start=src_dir)
                zf.write(local_path, archive_dest)
