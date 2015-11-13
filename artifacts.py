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
import logging
import shutil
import subprocess
import zipfile
from collections import namedtuple
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)

Artifact = namedtuple('Artifact', ['addon_id', 'version', 'git_repo', 'treeish'])


def pack_textures(working_dir):
    tree = ET.parse(os.path.join(working_dir, 'addon.xml'))
    is_skin = tree.find("./extension[@point='xbmc.gui.skin']") is not None
    compile = tree.find("./extension[@compile='true']") is not None

    if is_skin:
        invoke_texturepacker(os.path.join(working_dir, 'media'),
                os.path.join(working_dir, 'media', 'Textures.xbt'))

        if os.path.exists(os.path.join(working_dir, 'themes')):
            for theme_name in os.listdir(os.path.join(working_dir, 'themes')):
                invoke_texturepacker(os.path.join(working_dir, 'themes', theme_name),
                        os.path.join(working_dir, 'themes', theme_name + '.xbt'))

        _remove_non_xbt_files(os.path.join(working_dir, 'media'))
        _remove_non_xbt_files(os.path.join(working_dir, 'themes'))

    if compile:
        invoke_texturepacker(os.path.join(working_dir, 'resources'),
                os.path.join(working_dir, 'resources', 'Textures.xbt'))
        _remove_non_xbt_files(os.path.join(working_dir, 'resources'))


def _remove_non_xbt_files(directory):
    for root, dirs, files in os.walk(directory, topdown=False):
        for name in files:
            if not name.endswith(".xbt"):
                os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))


def invoke_texturepacker(input, output):
    logger.debug("Running texturepacker on %s", input)
    cmd = ['TexturePacker', '-dupecheck', '-input', input, '-output', output]
    with open(os.devnull, 'w') as f:
        subprocess.check_call(cmd, stdout=f, stderr=f)


def pack_artifact(artifact, src_dir, dst_dir):
    pack_textures(src_dir)

    try:
        shutil.rmtree(os.path.join(src_dir, '_screenshots'))
    except OSError:
        pass

    # Write and compress files in working_dir to the final zip file
    dest_file = os.path.join(dst_dir, "%s-%s.zip" % (artifact.addon_id, artifact.version))
    with zipfile.ZipFile(dest_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(src_dir):
            for name in files:
                local_path = os.path.join(root, name)
                archive_dest = artifact.addon_id + '/' + os.path.relpath(local_path, start=src_dir)
                zf.write(local_path, archive_dest)

    # Copy extra files
    if os.path.exists(os.path.join(src_dir, "icon.png")):
        shutil.copyfile(os.path.join(src_dir, "icon.png"), os.path.join(dst_dir, "icon.png"))

    if os.path.exists(os.path.join(src_dir, "fanart.jpg")):
        shutil.copyfile(os.path.join(src_dir, "fanart.jpg"), os.path.join(dst_dir, "fanart.jpg"))

    if os.path.exists(os.path.join(src_dir, "changelog.txt")):
        shutil.copyfile(os.path.join(src_dir, "changelog.txt"), os.path.join(dst_dir, "changelog-%s.txt" % artifact.version))
