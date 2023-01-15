import sys
from git import Repo, config, GitCommandError
from configparser import NoOptionError
from termcolor import colored

_NONE = object()
global_section_name = 'check-settings'
class ConfigNotFound(Exception):
    pass

def get_config_value(config, key, default=_NONE):
    """
    Returns a check-submodules option, retreived from .gitmodules

    check-submodules options are set in .gitmodules. For each option,
    it first searches in submodule config.
    If not found, it searches in a top section called after `global_section_name`.
    If not found, it returns default value if set, or raise an exception.

    config is a submodule config_reader object. It can be noted that a submodule config
    is actually the global .gitmodules parsed constrained within submodule section.
    config.config is the unconstrained global .gitmodules parsed file.
    """
    try:
        return config.get(key)
    except NoOptionError:
        try:
            return config.config.get(global_section_name, key)
        except NoOptionError:
            if default is not _NONE:
                return default
            raise ConfigNotFound(f"config '{key}' not found")

def errormsg(msg):
    return colored("ERROR: ", 'red') + msg

def print_error(msg):
    print(errormsg(msg))

def check_submodule_branch():
    repo = Repo()
    error = False

    for submodule in repo.submodules:
        config = submodule.config_reader()
        check_ref = get_config_value(config, 'check-ref')
        check_op = get_config_value(config, 'check-op')
        check_reftype = get_config_value(config, 'check-reftype', 'branch')
        submodule_repo = submodule.module()
        if check_reftype == 'branch':
            remote_refs = submodule_repo.remote().refs
        else:
            remote_refs = submodule_repo.tags
        if check_ref not in remote_refs:
            print_error(f'Submodule {submodule.name} {check_reftype} {check_ref} not found on remote repository.')
            error = True
            continue
        remote_ref = remote_refs[check_ref]
        remote_ref_sha1 = remote_ref.commit.hexsha
        current_commit = submodule.hexsha
        if check_op == 'ontop':
            if current_commit != remote_ref_sha1:
                print_error(f'Submodule {submodule.name} is not on top of {check_reftype} {check_ref} (currently on {current_commit})')
                error = True
                continue
        elif check_op == 'within':
            try:
                submodule_repo.git.merge_base(current_commit, remote_ref_sha1, is_ancestor=True)
            except GitCommandError:
                print_error(f'Submodule {submodule.name} is not contained in {check_reftype} {check_ref} (currently on {current_commit})')
                error = True
                continue
        else:
            print_error(f"Submodule {submodule.name} Unsupported check-op {check_op}")
            error = True
            continue
    if error:
        sys.exit(1)

check_submodule_branch()

