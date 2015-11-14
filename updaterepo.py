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
import git
import logging
import gitutils
from distutils.version import LooseVersion
from xml_index import create_index

try:
    from ConfigParser import ConfigParser
except ImportError:
    from configparser import ConfigParser
from collections import namedtuple


master_repo = "/home/git/addons-git/scripts"
remote_name = "origin"
config_branch = "master"
config_file = "targets.cfg"
fetch = True
verbosity = logging.DEBUG
outdir = "/var/www/downloads/addons"

extra_repos = [
    "/home/git/addons-git/plugins",
    "/home/git/addons-git/skins",
    "/home/git/addons-git/scrapers",
    "/home/git/addons-git/webinterfaces",
    "/home/git/addons-git/resources",
]

logger = logging.getLogger(__name__)
logging.basicConfig(level=verbosity, format="%(levelname)s: %(message)s")

Target = namedtuple('Target', ['name', 'branches', 'min_versions'])


def read_targets():
    """
    Reads config file from master git repo and return the targets to generate
    addon repository for.
    """
    config = ConfigParser({'branches': None, 'minversions': None})
    ref = remote_name + '/' + config_branch
    repo = git.Repo(master_repo)
    # python 2 workaround
    content = repo.refs[ref].commit.tree[config_file].data_stream.read()
    config.readfp(BytesIO(content))

    for target in config.sections():
        if '/' in target:
            continue
        branches = [b.strip(' \n\r') for b in config.get(target, 'branches').split(',')]
        min_versions = {}
        if config.get(target, 'minversions'):
            for version_string in config.get(target, 'minversions').split(','):
                id_part, version_part = version_string.strip(' \n\r').split(':', 1)
                id_part = id_part.strip(' \n\r')
                version_part = version_part.strip(' \n\r')
                min_versions[id_part] = LooseVersion(version_part)
        yield Target(target, branches, min_versions)


def update_all_targets():
    if fetch:
        for path in [master_repo] + extra_repos:
            repo = git.Repo(path)
            repo.remotes[remote_name].fetch()

    current_targets = list(read_targets())

    # Delete targets that have been removed since last update
    previous_targets = [name for name in os.listdir(outdir) if name != '.git']
    removed_targets = set(previous_targets) - set([t.name for t in current_targets])
    for target in removed_targets:
        logging.info("removing target '%s'", target)
        shutil.rmtree(os.path.join(outdir, target))

    # Now update the active ones
    for target in current_targets:
        refs = [remote_name + '/' + branch for branch in target.branches]
        dest = os.path.join(outdir, target.name)
        logging.info("Updating target '%r'. destination: %s", target, dest)
        try:
            os.makedirs(dest)
        except OSError:
            pass

        gitutils.update_changed_artifacts([master_repo] + extra_repos, refs, target.min_versions, dest)
        gitutils.delete_old_artifacts(dest, 3)

        # Create addons.xml
        create_index(dest, os.path.join(dest, 'addons.xml'))


if __name__ == '__main__':
    update_all_targets()
