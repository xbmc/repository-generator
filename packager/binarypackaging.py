# -*- coding: utf-8 -*-
#
#     Copyright (C) 2018 Team Kodi
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

import logging
import os
import zipfile
from collections import namedtuple
from distutils.version import LooseVersion
from distutils.dir_util import copy_tree
from itertools import groupby
from xml.etree import ElementTree as ET

from packager import utils
from .utils import delete_companion_files, makedirs_ignore_errors, meets_version_requirements, pack_artifact


logger = logging.getLogger(__name__)

Artifact = namedtuple('Artifact', ['addon_id', 'version', 'location', 'platform'])


def split_version(path):
    return os.path.splitext(os.path.basename(path))[0].rsplit('-', 1)


def collect_artifacts(binary_repos, min_versions):
    for repo_path in binary_repos:
        if not os.path.isdir(repo_path):
            logger.warning("No such repo %s. Skipping.", repo_path)
            continue
        for addon_id in os.listdir(os.path.join(repo_path)):
            if os.path.isdir(os.path.join(repo_path, addon_id)):
                zips = [os.path.join(repo_path, addon_id, name)
                        for name in os.listdir(os.path.join(repo_path, addon_id))
                        if os.path.splitext(name)[1] == '.zip' and '-' in name]
                if len(zips) > 0:
                    zips.sort(key=lambda _: LooseVersion(split_version(_)[1]), reverse=True)
                    with zipfile.ZipFile(zips[0], 'r') as zf:
                        try:
                            tree = ET.fromstring(zf.read(os.path.join(addon_id.split('+')[0], 'addon.xml')))
                            version = tree.attrib['version'].encode('utf-8')

                            imports = [(elem.attrib['addon'], LooseVersion(elem.attrib.get('version', '0.0.0')))
                                       for elem in tree.findall('./requires/import')]
                            if meets_version_requirements(imports, min_versions):
                                yield Artifact(addon_id.split('+')[0], version, zips[0], addon_id.split('+')[1])
                        except (ET.ParseError, KeyError, IndexError) as e:
                            logging.exception("Failed to read addon info from '%s'. Skipping" % archive)
                            continue


def filter_latest_version(artifacts):
    artifacts = list(artifacts)
    artifacts.sort(key=lambda _: _.addon_id)
    for addon_id, versions in groupby(artifacts, key=lambda _: _.addon_id + _.platform):
        versions = list(versions)
        versions.sort(key=lambda _: LooseVersion(_.version), reverse=True)
        if len(versions) >= 2 and versions[0].version == versions[1].version:
            logger.warning("Duplicate artifact. I will pick one at random. First: %r. Second: %r", versions[0], versions[1])
        yield versions[0]


def write_artifact(artifact, outdir):
    # Reads artifact data from git and writes a zip file (and companion files) to `outdir`
    with utils.tempdir() as unpack_dir:
        with zipfile.ZipFile(artifact.location, 'r') as zf:
            zf.extractall(unpack_dir)

        with utils.tempdir() as package_dir:
            pack_artifact(artifact, os.path.join(unpack_dir, artifact.addon_id), package_dir)
            delete_companion_files(outdir)
            copy_tree(package_dir, outdir)


def update_changed_artifacts(binary_repos, min_versions, outdir):
    """ Returns a tuple with number of new and a list of all artifacts. """

    artifacts = list(collect_artifacts(binary_repos, min_versions))
    artifacts = list(filter_latest_version(artifacts))

    added = [a for a in artifacts if not os.path.exists(
        os.path.join(outdir, "%s+%s" % (a.addon_id, a.platform), "%s-%s.zip" % (a.addon_id, a.version)))]

    for artifact in added:
        logger.debug("New artifact %s+%s version %s", artifact.addon_id, artifact.platform, artifact.version)
        dest = os.path.join(outdir, "%s+%s" % (artifact.addon_id, artifact.platform))
        makedirs_ignore_errors(dest)
        try:
            write_artifact(artifact, dest)
        except Exception as ex:
            logger.error("Failed to package %s:", artifact, exc_info=1)

    return len(added), ['%s+%s' % (a.addon_id, a.platform) for a in artifacts]
