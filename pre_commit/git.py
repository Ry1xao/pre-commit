import functools
import logging
import os
import os.path
import re
from plumbum import local

from pre_commit.util import memoize_by_cwd


logger = logging.getLogger('pre_commit')


@memoize_by_cwd
def get_root():
    path = os.getcwd()
    while len(path) > 1:
        if os.path.exists(os.path.join(path, '.git')):
            return path
        else:
            path = os.path.normpath(os.path.join(path, '../'))
    raise AssertionError('called from outside of the gits')


def is_in_merge_conflict():
    return os.path.exists(os.path.join('.git', 'MERGE_MSG'))


def parse_merge_msg_for_conflicts(merge_msg):
    # Conflicted files start with tabs
    return [
        line.strip() for line in merge_msg.splitlines() if line.startswith('\t')
    ]


@memoize_by_cwd
def get_conflicted_files():
    # Need to get the conflicted files from the MERGE_MSG because they could
    # have resolved the conflict by choosing one side or the other
    merge_msg = open(os.path.join('.git', 'MERGE_MSG')).read()
    merge_conflict_filenames = parse_merge_msg_for_conflicts(merge_msg)

    # This will get the rest of the changes made after the merge.
    # If they resolved the merge conflict by choosing a mesh of both sides
    # this will also include the conflicted files
    tree_hash = local['git']['write-tree']().strip()
    merge_diff_filenames = local['git'][
        'diff', '-m', tree_hash, 'HEAD', 'MERGE_HEAD', '--name-only',
    ]().splitlines()
    return set(merge_conflict_filenames) | set(merge_diff_filenames)


@memoize_by_cwd
def get_staged_files():
    return local['git']['diff', '--staged', '--name-only']().splitlines()


@memoize_by_cwd
def get_all_files():
    return local['git']['ls-files']().splitlines()


def get_files_matching(all_file_list_strategy):
    @functools.wraps(all_file_list_strategy)
    @memoize_by_cwd
    def wrapper(include_expr, exclude_expr):
        include_regex = re.compile(include_expr)
        exclude_regex = re.compile(exclude_expr)
        return set(
            filename
            for filename in all_file_list_strategy()
            if (
                include_regex.search(filename) and
                not exclude_regex.search(filename) and
                os.path.exists(filename)
            )
        )
    return wrapper


get_staged_files_matching = get_files_matching(get_staged_files)
get_all_files_matching = get_files_matching(get_all_files)
get_conflicted_files_matching = get_files_matching(get_conflicted_files)
