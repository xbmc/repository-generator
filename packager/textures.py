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
import subprocess

logger = logging.getLogger(__name__)


def pack_textures(xml, working_dir):
    is_skin = xml.find("./extension[@point='xbmc.gui.skin']") is not None
    compile = xml.find("./extension[@compile='true']") is not None

    if is_skin:
        run_texturepacker(os.path.join(working_dir, 'media'),
                          os.path.join(working_dir, 'media', 'Textures.xbt'))

        if os.path.exists(os.path.join(working_dir, 'themes')):
            for theme_name in os.listdir(os.path.join(working_dir, 'themes')):
                run_texturepacker(os.path.join(working_dir, 'themes', theme_name),
                                  os.path.join(working_dir, 'media', theme_name + '.xbt'))

        remove_non_xbt_files(os.path.join(working_dir, 'media'))
        remove_non_xbt_files(os.path.join(working_dir, 'themes'))

    if compile:
        run_texturepacker(os.path.join(working_dir, 'resources'),
                          os.path.join(working_dir, 'resources', 'Textures.xbt'))
        remove_non_xbt_files(os.path.join(working_dir, 'resources'))


def remove_non_xbt_files(directory):
    for root, dirs, files in os.walk(directory, topdown=False):
        for name in files:
            if not name.endswith(".xbt"):
                os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))


def run_texturepacker(input, output):
    logger.debug("Running texturepacker on %s ...", input)
    cmd = ['TexturePacker', '-dupecheck', '-input', input, '-output', output]
    with open(os.devnull, 'w') as f:
        subprocess.check_call(cmd, stdout=f, stderr=f)
