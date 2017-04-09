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
import shutil
import git
import sys
import logging
import packager
from distutils.version import LooseVersion
from io import BytesIO

try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser
from collections import namedtuple


Target = namedtuple('Target', ['name', 'branches', 'min_versions'])


config = ConfigParser()
logger = logging.getLogger("updaterepo")


def read_targets():
    """
    Reads config file from the remove git configuration repo and returns the targets to generate
    addon repository for.
    """
    repo = git.Repo(config.get('configuration_repo', 'location'))
    remote_name = config.get('configuration_repo', 'remote_name')
    ref = remote_name + '/' + config.get('configuration_repo', 'branch')
    filename = config.get('configuration_repo', 'filename')

    if config.getboolean('debug', 'fetch_remotes'):
        repo.remotes[remote_name].fetch()

    # python 2 workaround
    content = repo.refs[ref].commit.tree[filename].data_stream.read()
    target_config = ConfigParser({'branches': None, 'minversions': None})
    target_config.readfp(BytesIO(content))

    for target in target_config.sections():
        if '/' in target:
            continue
        branches = [b.strip(' \n\r') for b in target_config.get(target, 'branches').split(',')]
        min_versions = {}
        if target_config.get(target, 'minversions'):
            for version_string in target_config.get(target, 'minversions').split(','):
                id_part, version_part = version_string.strip(' \n\r').split(':', 1)
                id_part = id_part.strip(' \n\r')
                version_part = version_part.strip(' \n\r')
                min_versions[id_part] = LooseVersion(version_part)
        yield Target(target, branches, min_versions)


def update_all_targets():
    remote_name = config.get('source_repo', 'remote_name')
    outdir = config.get('general', 'destination')
    version_to_keep = config.getint('general', 'version_to_keep')
    source_locations = config.get('source_repo', 'locations').replace('\n', '').split(',')

    if not outdir:
        logger.fatal("No destination specified.")
        return

    if config.getboolean('debug', 'fetch_remotes'):
        for path in source_locations:
            git.Repo(path).remotes[remote_name].fetch()

    current_targets = list(read_targets())

    # Delete targets that have been removed since last update
    previous_targets = [name for name in os.listdir(outdir) if not name.startswith('.')]
    removed_targets = set(previous_targets) - set([t.name for t in current_targets])
    for target in removed_targets:
        logger.debug("Deleting unknown target %s", target)
        shutil.rmtree(os.path.join(outdir, target))

    # Now update the active ones
    for target in current_targets:
        refs = [remote_name + '/' + branch for branch in target.branches]
        dest = os.path.join(outdir, target.name)
        logger.debug("============================ %s ============================", target.name)
        logger.debug("Branches: %s", target.branches)
        logger.debug("Min. versions: %s", target.min_versions)
        logger.debug("Destination: %s", dest)
        try:
            os.makedirs(dest)
        except OSError:
            pass

        added, removed = packager.update_changed_artifacts(source_locations, refs, target.min_versions, dest)
        logger.debug("Results: %d artifacts added, %d artifacts removed", added, removed)

        logger.debug("Purging old artifact version... To keep: %d", version_to_keep)
        packager.delete_old_artifacts(dest, version_to_keep)


def main():
    filename = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), 'config.cfg')
    if not config.read(filename):
        print("Fatal: Could not read config file '%s'" % filename)
        sys.exit(1)

    logging.basicConfig(level=config.getint('debug', 'level'), format='%(levelname)s [%(name)s] %(message)s')
    update_all_targets()

if __name__ == '__main__':
    main()
