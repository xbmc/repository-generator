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
import logging
import gitbridge
import git
from argparse import ArgumentParser

git_repos = [
    "/home/git/addons-git/plugins",
    "/home/git/addons-git/scripts",
    "/home/git/addons-git/resources",
    "/home/git/addons-git/skins",
    "/home/git/addons-git/scrapers",
    "/home/git/addons-git/webinterfaces",
]

refs = [
    "origin/gotham",
    "origin/helix",
    "origin/isengard",
    "origin/jarvis",
]

remote = "origin"
outdir = "/var/www/downloads/addons"

targets = [
    (git_repos, refs[0:4], os.path.join(outdir, 'j')),
]

def main():
    parser = ArgumentParser(description="", add_help=True)
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', default=False)
    parser.add_argument('--no-fetch', dest='fetch', action='store_false', default=True,
                        help="Don't fetch remotes before writing changes")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
            format="%(levelname)s: %(message)s")

    if args.fetch:
        for path in git_repos:
            repo = git.Repo(path)
            repo.remotes[remote].fetch()

    for repos, refs, outdir, in targets:
        gitbridge.update_changed_artifacts(repos, refs, outdir)
        gitbridge.purge_old_artifacts(outdir, versions_to_keep=3)


if __name__ == '__main__':
    main()
