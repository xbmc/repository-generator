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
import logging
from distutils.version import LooseVersion
from packager import gitpackaging

logger = logging.getLogger(__name__)


def update_changed_artifacts(git_repos, refs, min_versions, outdir):
    """ Returns a tuple with number of new and deleted artifacts. """

    current = set([name for name in os.listdir(outdir)
                   if os.path.isdir(os.path.join(outdir, name)) and not name.startswith('.')])

    added, artifacts = gitpackaging.update_changed_artifacts(git_repos, refs, min_versions, outdir)

    removed = current - set(artifacts)
    for artifact_id in removed:
        logger.debug("Removing artifact %s", artifact_id)
        shutil.rmtree(os.path.join(outdir, artifact_id))

    return added, len(removed)


def delete_old_artifacts(target_dir, versions_to_keep):
    for artifact_id in os.listdir(target_dir):
        artifact_dir = os.path.join(target_dir, artifact_id)
        if not os.path.isdir(artifact_dir):
            continue

        zips = [name for name in os.listdir(artifact_dir) if os.path.splitext(name)[1] == '.zip']
        if len(zips) <= versions_to_keep:
            continue

        version_from_name = lambda name: os.path.splitext(name)[0].rsplit('-', 1)[1]
        zips.sort(key=lambda _: LooseVersion(version_from_name(_)), reverse=True)

        for filename in zips[versions_to_keep:]:
            logger.debug("Removing old artifact %s", filename)
            os.remove(os.path.join(artifact_dir, filename))

            # TODO: remove after krypton
            changelog = os.path.join(artifact_dir, 'changelog-%s.txt' % version_from_name(filename))
            if os.path.exists(changelog):
                os.remove(changelog)
