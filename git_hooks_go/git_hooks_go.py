# -*- coding: utf-8 -*-
import ConfigParser
import os

import re
import shutil
import sys

project_home = os.path.split(os.path.realpath(__file__))[0].split('.git')[0]

config_path = os.path.join(project_home, '.git/hooks/config.ini')


# 清除记事本自动添加的BOM
with open(config_path) as f:
    content = f.read()
content = re.sub(r"\xfe\xff", "", content)
content = re.sub(r"\xff\xfe", "", content)
content = re.sub(r"\xef\xbb\xbf", "", content)
with open(config_path, 'w') as f:
    f.write(content)


def copytree2(src, dst, symlinks=False, ignore=None):
    names = os.listdir(src)
    if ignore is not None:
        ignored_names = ignore(src, names)
    else:
        ignored_names = set()
    if not os.path.isdir(dst):
        os.makedirs(dst)
    errors = []
    for name in names:
        if name in ignored_names:
            continue
        srcname = os.path.join(src, name)
        dstname = os.path.join(dst, name)
        try:
            if symlinks and os.path.islink(srcname):
                linkto = os.readlink(srcname)
                os.symlink(linkto, dstname)
            elif os.path.isdir(srcname):
                copytree2(srcname, dstname, symlinks, ignore)
            else:
                # Will raise a SpecialFileError for unsupported file types
                shutil.copy2(srcname, dstname)
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except shutil.Error, err:
            errors.extend(err.args[0])
        except EnvironmentError, why:
            errors.append((srcname, dstname, str(why)))
    try:
        shutil.copystat(src, dst)
    except OSError, why:
        if WindowsError is not None and isinstance(why, WindowsError):
            # Copying file access times may fail on Windows
            pass
        else:
            errors.append((src, dst, str(why)))
    if errors:
        raise shutil.Error, errors


def get_config():
    try:
        config = ConfigParser.ConfigParser()
        config.read(config_path)
        auto_update = config.get('config', 'auto_update').strip()
        update_config = config.get('config', 'update_config').strip()
        return auto_update, update_config
    except BaseException as e:
        print(e)
        return None, None


def get_selected_scripts(script_type):
    try:
        config = ConfigParser.ConfigParser()
        config.read(config_path)
        scripts = config.get('selected_scripts', script_type).split(',')
        return scripts
    except BaseException as e:
        print(e)
        return []


def run_scripts(script_type, scripts):
    for script in scripts:
        execfile('.git/hooks/%s-scripts/%s.py' % (script_type, script))


src_path = os.path.join(project_home, 'git_hooks_go')
hooks_path = os.path.join(project_home, '.git/hooks')


def update_git_hooks_go():
    auto_update, update_config = get_config()
    if auto_update == '1':
        if update_config == '1':
            copytree2(src_path, hooks_path)
        else:
            copytree2(src_path, hooks_path, ignore=shutil.ignore_patterns('config.ini'))


def go(script_type):
    print('git-hooks-go has run.')
    if script_type in ['post-merge', 'post-checkout', 'post-rewrite']:
        update_git_hooks_go()
    scripts = get_selected_scripts(script_type)

    run_scripts(script_type, scripts)
