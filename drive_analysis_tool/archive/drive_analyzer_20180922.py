import os
import statistics
import pickle


def record_stat(root):
    # Do a walk from the root folder and collect statistics of all the files within each subfolder.
    # For the sake of anonymity, file names are not stored.
    # Folder names are stored but users can opt out and choose alternative names.
    # Folders can be excluded from the tree.
    dir_dict = dict()
    order_dict = dict()
    dirorder = 1  # key starts as 1 since 0 can be interpreted as a boolean False
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        invalid_dirs = []
        for dir_ in dirnames:
            try:
                os.scandir(os.path.join(dirpath, dir_))
            except PermissionError:
                invalid_dirs.append(dir_)
        dirnames = list(set(dirnames).difference(set(invalid_dirs)))
        dirnames[:] = [dir_ for dir_ in dirnames if dir_[0] != '.']
        filenames[:] = [file for file in filenames if file[0] != '.']
        if dirorder == 1:
            dirparent = False  # signifies node as top-level, so it has no parent
        else:
            dirparent = os.path.split(dirpath)[0]
        filestat_list = []
        for f_ in filenames:
            f_path = os.path.join(dirpath, f_)
            if os.access(f_path, os.R_OK):
                try:
                    filestat_list.append(os.stat(f_path))
                except OSError:
                    pass
        dir_dict[dirorder] = {'dirname': os.path.split(dirpath)[1],  # directory name [0]
                              'dirparent': dirparent,  # parent key [1]
                              'childkeys': [os.path.join(dirpath, dir_) for dir_ in dirnames],  # children keys [2]
                              # 'files': filenames,  # names of files found in directory [3]
                              'nfiles': len(filenames),  # number of files found in directory [3]
                              'cumfiles': len(filenames),  # cumulative count of accessible files [4]
                              # 'filestat':  {f_: os.stat(os.path.join(dirpath, f_)) for f_ in filenames},
                              # 'filestat': [os.stat(os.path.join(dirpath, f_)) for f_ in filenames],
                              # statistics for each file in the folder [5]
                              'filestat': filestat_list,  # statistics for each file in the folder [5]
                              'aggfilestat': None}  # aggregated statistics for a folder's files [6]
        order_dict[dirpath] = dirorder
        dirorder += 1

    # Refer to each node using a unique key instead of dirpath
    for dirkey in sorted(dir_dict.keys()):
        if dirkey > 1:
            # dir_dict[dirkey][1] = order_dict[dir_dict[dirkey][1]]
            dir_dict[dirkey]['dirparent'] = order_dict[dir_dict[dirkey]['dirparent']]
        # dir_dict[dirkey][2] = [order_dict[child] for child in dir_dict[dirkey][2]]
        dir_dict[dirkey]['childkeys'] = [order_dict[child] for child in dir_dict[dirkey]['childkeys']]

    # print_tree(root, dir_dict)
    # print('\n')

    return dir_dict


def compute_stat(dir_dict):
    # Count cumulative accessible files
    for dirkey in sorted(dir_dict.keys(), reverse=True):
        # children = dir_dict[dirkey][2]
        # dir_dict[dirkey][4] += sum([dir_dict[child][4] for child in children])
        children = dir_dict[dirkey]['childkeys']
        dir_dict[dirkey]['cumfiles'] += sum([dir_dict[child]['cumfiles'] for child in children])
        all_st_atime = []
        all_st_mtime = []
        all_st_ctime = []
        # for f_ in dir_dict[dirkey]['files']:
        #     all_st_atime.append(dir_dict[dirkey]['filestat'][f_].st_atime)
        #     all_st_mtime.append(dir_dict[dirkey]['filestat'][f_].st_mtime)
        #     all_st_ctime.append(dir_dict[dirkey]['filestat'][f_].st_ctime)
        for stat_ in dir_dict[dirkey]['filestat']:
            all_st_atime.append(stat_.st_atime)
            all_st_mtime.append(stat_.st_mtime)
            all_st_ctime.append(stat_.st_ctime)
        try:
            agg_atime = statistics.median(all_st_atime)
        except statistics.StatisticsError:
            agg_atime = None
        try:
            agg_mtime = statistics.median(all_st_mtime)
        except statistics.StatisticsError:
            agg_mtime = None
        try:
            agg_ctime = statistics.median(all_st_ctime)
        except statistics.StatisticsError:
            agg_ctime = None
        dir_dict[dirkey]['aggfilestat'] = {'aggatime': agg_atime,
                                           'aggmtime': agg_mtime,
                                           'aggctime': agg_ctime}

    return dir_dict


def find_all_children(dirkey, dir_dict):
    children = []
    for child in dir_dict[dirkey][2]:
        children.extend(find_all_children(child, dir_dict))
    children.extend(dir_dict[dirkey][2])
    return children


def anonymize_stat_old(dir_dict, rename_dict, remove_dict):
    # Anonymize dir_dict by removing some dirs and renaming some dirs.
    # If a directory is removed, remove its children and remove its parent's reference to it.
    for dirkey in rename_dict.keys():
        dir_dict[dirkey]['dirname'] = rename_dict[dirkey]['dirname']
    for dirkey in sorted(remove_dict.keys()):
        children = find_all_children(dirkey, dir_dict)
        parent = dir_dict['dirparent']
        for child in children:
            dir_dict.pop(child)
        dir_dict[parent]['childkeys'] = list(set(dir_dict[parent]['childkeys']).difference(set([dirkey])))
    return dir_dict


def anonymize_stat(dir_dict, removed_dirs, renamed_dirs=None):
    # Anonymize dir_dict by removing some dirs and renaming some dirs.
    # If a directory is removed, remove its children and remove its parent's reference to it.
    if renamed_dirs is not None:
        for dirkey in renamed_dirs.keys():
            dir_dict[dirkey]['dirname'] = renamed_dirs[dirkey]
    for dirkey in list(removed_dirs):
        parent = dir_dict[dirkey]['dirparent']
        if parent in dir_dict.keys():
            og_childset = set(dir_dict[parent]['childkeys'])
            rm_childset = set([dirkey])
            dir_dict[parent]['childkeys'] = list(og_childset.difference(rm_childset))
            # dir_dict[parent]['childkeys'] = list(set(dir_dict[parent]['childkeys']).difference(set([dirkey])))
        dir_dict.pop(dirkey)
    return dir_dict


if __name__ == "__main__":
    root_path = os.path.expanduser(os.path.join('~', 'Dropbox', 'mcgill'))
    # root_path = os.path.expanduser(os.path.join('~', 'Downloads'))
    dir_dict = record_stat(root_path)
    # dir_dict = compute_stat(dir_dict)
    with open(os.path.expanduser(os.path.join('~', 'Dropbox', 'mcgill', 'File Zoomer',
                                              'code', 'drive_analysis_tool', 'dir_dict.pkl')), 'wb') as ddf:
        pickle.dump(dir_dict, ddf, pickle.HIGHEST_PROTOCOL)
    # with open(os.path.expanduser(os.path.join('~', 'Dropbox', 'mcgill', 'File Zoomer',
    #                                           'code', 'drive_analysis_tool', 'dir_dict.pkl')), 'rb') as ddf:
    #     dir_dict = pickle.load(ddf)
    anonymize_stat(dir_dict, [1, 3, 5])
