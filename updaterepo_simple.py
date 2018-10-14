#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Thomas Amland
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
import hashlib
import logging
from indexer.indexer import create_index
import packager

logger = logging.getLogger("updaterepo")


def main():
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s [%(name)s] %(message)s')
    source = sys.argv[1]
    outdir = sys.argv[2]

    added, removed = packager.update_changed_artifacts([source], ['master'], [], [], outdir)
    logger.debug("Results: %d artifacts added, %d artifacts removed", added, removed)

    if added or removed:
        packager.delete_old_artifacts(outdir, 1)

        create_index(outdir, os.path.join(outdir, "addons.xml"))
        md5sum = hashlib.md5()
        with open(os.path.join(outdir, "addons.xml.gz"), 'rb') as f:
            md5sum.update(f.read())
        with open(os.path.join(outdir, "addons.xml.gz.md5"), 'wb') as f:
            f.write(md5sum.hexdigest())


if __name__ == '__main__':
    main()
