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

import git
import logging
import os
import shutil
import zipfile
from distutils.version import LooseVersion
from distutils.dir_util import copy_tree
from io import BytesIO
from itertools import groupby
from xml.etree import ElementTree as ET

from packager import utils
from .utils import makedirs_ignore_errors
from packaging import Artifact, pack_artifact, meets_version_requirements
from packager.packaging import delete_companion_files

logger = logging.getLogger(__name__)


def collect_artifacts(git_repos, refs, min_versions):
    for repo_path in git_repos:
        repo = git.Repo(repo_path)
        if repo.bare:
            logger.warning("Repo %s is bare, Skipping", repo_path)
            continue
        for ref in refs:
            if ref not in repo.refs:
                logger.warning("No such ref %s in repo %s. Skipping.", ref, repo_path)
                continue
            for directory in repo.refs[ref].commit.tree.trees:
                try:
                    addon_xml = directory['addon.xml'].data_stream.read()
                    tree = ET.fromstring(addon_xml)
                    artifact_id = directory.name.encode('utf-8')
                    version = tree.attrib['version'].encode('utf-8')

                    imports = [(elem.attrib['addon'], LooseVersion(elem.attrib.get('version', '0.0.0')))
                               for elem in tree.findall('./requires/import')]
                    if meets_version_requirements(imports, min_versions):
                        yield Artifact(artifact_id, version, repo_path, ref + ":" + artifact_id)
                except (ET.ParseError, KeyError, IndexError) as e:
                    logger.exception("Failed to read addon data from directory '%s'" % directory.name.encode('utf-8'))


def filter_latest_version(artifacts):
    artifacts = list(artifacts)
    artifacts.sort(key=lambda _: _.addon_id)
    for addon_id, versions in groupby(artifacts, key=lambda _: _.addon_id):
        versions = list(versions)
        versions.sort(key=lambda _: LooseVersion(_.version), reverse=True)
        if len(versions) >= 2 and versions[0].version == versions[1].version:
            logger.warning("Duplicate artifact. I will pick one at random. First: %r. Second: %r", versions[0], versions[1])
        yield versions[0]


def write_artifact(artifact, outdir, linkdir = None):
    """ Reads artifact data from git and writes a zip file (and companion files) to `outdir` """
    repo = git.Repo(artifact.git_repo)
    with utils.tempdir() as unpack_dir:
        buffer = BytesIO()
        repo.archive(buffer, artifact.treeish, format="zip")
        with zipfile.ZipFile(buffer, 'r') as zf:
            zf.extractall(unpack_dir)

        with utils.tempdir() as package_dir:
            pack_artifact(artifact, unpack_dir, package_dir, linkdir)
            delete_companion_files(outdir)
            for item in os.listdir(package_dir):
                shutil.move(os.path.join(package_dir, item), outdir)


def update_changed_artifacts(git_repos, refs, min_versions, outdir, target_branch):
    """ Returns a tuple with number of new and deleted artifacts. """
    artifacts = collect_artifacts(git_repos, refs, min_versions)
    artifacts = list(filter_latest_version(artifacts))

    added = [a for a in artifacts if not os.path.exists(
        os.path.join(outdir, a.addon_id, "%s-%s.zip" % (a.addon_id, a.version)))]
    current = set([name for name in os.listdir(outdir)
                   if os.path.isdir(os.path.join(outdir, name)) and not name.startswith('.')])
    removed = current - set([_.addon_id for _ in artifacts])

    for artifact in added:
        logger.debug("New artifact %s version %s", artifact.addon_id, artifact.version)
        dest = os.path.join(outdir, artifact.addon_id)
        original_branch = artifact.treeish.split(':')[0].split('/')[-1]
        linkdir = os.path.join('..', '..', original_branch, artifact.addon_id)
        makedirs_ignore_errors(dest)
        try:
            write_artifact(artifact, dest, linkdir if target_branch != original_branch else None)
        except Exception as ex:
            logger.error("Failed to package %s:", artifact, exc_info=1)

    for artifact_id in removed:
        logger.debug("Removing artifact %s", artifact_id)
        shutil.rmtree(os.path.join(outdir, artifact_id))

    return len(added), len(removed)
