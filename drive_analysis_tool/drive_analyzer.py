import os
import sys
import ctypes
import statistics
import pickle
from collections import Counter


def record_stat(root):
    """ Do a walk from the root folder and collect statistics of all the files
    within each subfolder. For the sake of anonymity, file names are not
    stored. Folder names are stored but users can opt out and choose
    alternative names. Folders can be excluded from the tree. """
    dir_dict = dict()
    order_dict = dict()
    dirorder = 1  # key starts at 1 as 0 can be interpreted as boolean False
    hidden_dirs = []
    for dirpath, dirnames, filenames in os.walk(
            root, topdown=True, followlinks=False):
        invalid_dirs = []
        for dir_ in dirnames:
            try:
                os.scandir(os.path.join(dirpath, dir_))
            except PermissionError:
                invalid_dirs.append(dir_)
        dirnames = list(set(dirnames).difference(set(invalid_dirs)))
        hidden_dirs += [os.path.join(dirpath, dir_) for dir_ in dirnames
                        if is_hidden_item(dirpath, dir_)]
        dirnames[:] = [dir_ for dir_ in dirnames
                       if not is_hidden_item(dirpath, dir_)]
        filenames[:] = [file for file in filenames
                        if not is_hidden_item(dirpath, file)]
        if dirorder == 1:
            dirparent = False  # marks node as top-level, so it has no parent
        else:
            dirparent = os.path.split(dirpath)[0]
        filestat_list = []
        for f_ in filenames:
            f_path = os.path.join(dirpath, f_)
            if os.access(f_path, os.R_OK):
                try:
                    f_stat = os.stat(f_path)
                    # [f_stat.st_mode, f_stat.st_ino,
                    #  f_stat.st_dev, f_stat.st_nlink, f_stat.st_uid, f_stat.st_gid, f_stat.st_size,
                    #  f_stat.st_atime, f_stat.st_mtime, f_stat.st_ctime,
                    #  f_stat.st_atime_ns, f_stat.st_mtime_ns, f_stat.st_ctime_ns,
                    #  f_stat.st_file_attributes]
                    filestat_list.append({'mode': f_stat.st_mode,
                                          'ino': f_stat.st_ino,
                                          'dev': f_stat.st_dev,
                                          'nlink': f_stat.st_nlink,
                                          'uid': f_stat.st_uid,
                                          'gid': f_stat.st_gid,
                                          'size': f_stat.st_size,
                                          'atime': f_stat.st_atime,
                                          'mtime': f_stat.st_mtime,
                                          'ctime': f_stat.st_ctime
                                          # 'file_attributes': f_stat.st_file_attributes
                                          })
                except OSError:
                    pass
        dir_dict[dirorder] = {'dirname': os.path.split(dirpath)[1],  # directory name [0]
                              'dirparent': dirparent,  # parent key [1]
                              'childkeys': [os.path.join(dirpath, dir_) for dir_ in dirnames],  # children keys [2]
                              'depth': 0,  # current folder's depth
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

    # Remove hidden dirs and their children
    hidden_dirs = [order_dict[dirpath] for dirpath in hidden_dirs]
    for dirkey in hidden_dirs:
        hidden_dirs += find_all_children(dirkey, dir_dict)
    hidden_dirs = list(set(hidden_dirs))
    for dirkey in hidden_dirs:
        dir_dict.pop(dirkey)

    # print_tree(root, dir_dict)
    # print('\n')
    assign_folder_depth(1, dir_dict)
    return dir_dict


def is_hidden_item(root, f):
    """ checks to see if file or folder is hidden (OS-sensitive)
    https://github.com/jddinneen/cardinal/blob/master/src/walk.py """
    if sys.platform in ['Windows',  'win32']:
        try:
            full_path = os.path.join(root, f)
            attrs = ctypes.windll.kernel32.GetFileAttributesW(full_path)
            assert attrs != -1
            result = bool(attrs & 2)
        except (AttributeError, AssertionError):
            result = False
        return result
    else:
        # POSIX style hidden files.
        # TODO: add provision for mac 'hidden' flag as users can manually
        # hide folders using this mac-specific flag.
        if str(f).startswith('.'):
            return True
        else:
            return False


def assign_folder_depth(dirkey, dir_dict):
    if dir_dict[dirkey]['dirparent']:
        dir_dict[dirkey]['depth'] = dir_dict[dir_dict[dirkey]['dirparent']]['depth'] + 1
    for child in dir_dict[dirkey]['childkeys']:
        assign_folder_depth(child, dir_dict)


def compute_stat(dir_dict):
    # Count cumulative accessible files
    for dirkey in sorted(dir_dict.keys(), reverse=True):
        # children = dir_dict[dirkey][2]
        # dir_dict[dirkey][4] += sum([dir_dict[child][4] for child in children])
        children = dir_dict[dirkey]['childkeys']
        dir_dict[dirkey]['cumfiles'] += sum([dir_dict[child]['cumfiles'] for child in children])
        all_atime = []
        all_mtime = []
        all_ctime = []
        # for f_ in dir_dict[dirkey]['files']:
        #     all_st_atime.append(dir_dict[dirkey]['filestat'][f_].st_atime)
        #     all_st_mtime.append(dir_dict[dirkey]['filestat'][f_].st_mtime)
        #     all_st_ctime.append(dir_dict[dirkey]['filestat'][f_].st_ctime)
        for stat_ in dir_dict[dirkey]['filestat']:
            all_atime.append(stat_['atime'])
            all_mtime.append(stat_['mtime'])
            all_ctime.append(stat_['ctime'])
        try:
            agg_atime = statistics.median(all_atime)
        except statistics.StatisticsError:
            agg_atime = None
        try:
            agg_mtime = statistics.median(all_mtime)
        except statistics.StatisticsError:
            agg_mtime = None
        try:
            agg_ctime = statistics.median(all_ctime)
        except statistics.StatisticsError:
            agg_ctime = None
        dir_dict[dirkey]['aggfilestat'] = {'aggatime': agg_atime,
                                           'aggmtime': agg_mtime,
                                           'aggctime': agg_ctime}
    return dir_dict


def find_all_children(dirkey, dir_dict):
    children = []
    for child in dir_dict[dirkey]['childkeys']:
        children.extend(find_all_children(child, dir_dict))
    children.extend(dir_dict[dirkey]['childkeys'])
    return children


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


def errant_mean(iterable):
    try:
        return statistics.mean(iterable)
    except statistics.StatisticsError:
        return None


def errant_mode(iterable):
    try:
        return statistics.mode(iterable)
    except statistics.StatisticsError:
        return None


def drive_measurement(dir_dict_list, allow_stat_error=False):
    # breadth_counts = []
    leaf_folder_depths = []
    switch_folder_depths = []
    branching_n_folder_counts = []
    n_file_counts = []
    folder_depths = []
    file_depths = []

    if allow_stat_error:
        mean_func = errant_mean
        mode_func = errant_mode
    else:
        mean_func = statistics.mean
        mode_func = statistics.mode

    n_roots = len(dir_dict_list)  # number of roots
    n_files = 0
    n_folders = sum([len(dir_dict.keys()) for dir_dict in dir_dict_list])
    # breadth_max = 0
    # breadth_mean = 0
    root_n_folders = sum([len(dir_dict[1]['childkeys']) for dir_dict in dir_dict_list])
    n_leaf_folders = 0
    # pct_leaf_folders = 0
    # depth_leaf_folders_mean = 0
    n_switch_folders = 0
    # pct_switch_folders = 0
    # depth_switch_folders_mean = 0
    # depth_max = 0
    # depth_folders_mode = 0
    # depth_folders_mean = 0
    # branching_factor = 0
    root_n_files = sum([dir_dict[1]['nfiles'] for dir_dict in dir_dict_list])
    # n_files_mean = 0
    n_empty_folders = 0
    # pct_empty_folders = 0
    # depth_files_mean = 0
    # depth_files_mode = 0
    file_breadth_mode_n_files = 0
    for dir_dict in dir_dict_list:
        for key in dir_dict.keys():
            n_files += dir_dict[key]['nfiles']
            n_file_counts.append(dir_dict[key]['nfiles'])
            # breadth_counts.append(len(dir_dict[key]['childkeys']))
            folder_depths.append(dir_dict[key]['depth'])
            if len(dir_dict[key]['childkeys']) == 0:  # identifies leaf nodes
                n_leaf_folders += 1
                leaf_folder_depths.append(dir_dict[key]['depth'])
                if dir_dict[key]['nfiles'] == 0:  # identifies empty folders
                    n_empty_folders += 1
                elif dir_dict[key]['nfiles'] > 0:
                    file_depths.append(dir_dict[key]['depth'])
            elif len(dir_dict[key]['childkeys']) > 0:  # not switch but not leaf nodes
                branching_n_folder_counts.append(len(dir_dict[key]['childkeys']))
                if dir_dict[key]['nfiles'] == 0:  # identifies switch nodes
                    n_switch_folders += 1
                    switch_folder_depths.append(dir_dict[key]['depth'])
                elif dir_dict[key]['nfiles'] > 0:
                    file_depths.append(dir_dict[key]['depth'])

    # breadth_max = max(breadth_counts)
    # breadth_mean = mean_func(breadth_counts)
    breadth_max = Counter(folder_depths).most_common(1)[0][1]
    breadth_mean = mean_func(Counter(folder_depths).values())
    pct_leaf_folders = n_leaf_folders / n_folders * 100
    depth_leaf_folders_mean = mean_func(leaf_folder_depths)
    pct_switch_folders = n_switch_folders / n_folders * 100
    depth_switch_folders_mean = mean_func(switch_folder_depths)
    depth_max = max(folder_depths)
    depth_folders_mode = mode_func(folder_depths)
    depth_folders_mean = mean_func(folder_depths)
    branching_factor = mean_func(branching_n_folder_counts)
    n_files_mean = mean_func(n_file_counts)
    pct_empty_folders = n_empty_folders / n_folders * 100
    depth_files_mean = mean_func(file_depths)
    depth_files_mode = mode_func(file_depths)

    for key in dir_dict.keys():
        if dir_dict[key]['depth'] == depth_files_mode:
            file_breadth_mode_n_files += dir_dict[key]['nfiles']
    labels = ['n_roots', 'n_files', 'n_folders', 'breadth_max', 'breadth_mean', 'root_n_folders', 'n_leaf_folders',
              'pct_leaf_folders', 'depth_leaf_folders_mean', 'n_switch_folders', 'pct_switch_folders',
              'depth_switch_folders_mean', 'depth_max', 'depth_folders_mode', 'depth_folders_mean',
              'branching_factor', 'root_n_files', 'n_files_mean', 'n_empty_folders', 'pct_empty_folders',
              'depth_files_mean', 'depth_files_mode', 'file_breadth_mode_n_files']
    values = [n_roots, n_files, n_folders, breadth_max, breadth_mean, root_n_folders, n_leaf_folders, pct_leaf_folders,
              depth_leaf_folders_mean, n_switch_folders, pct_switch_folders, depth_switch_folders_mean,
              depth_max, depth_folders_mode, depth_folders_mean, branching_factor, root_n_files, n_files_mean,
              n_empty_folders, pct_empty_folders, depth_files_mean, depth_files_mode, file_breadth_mode_n_files]
    return {label: value for label, value in zip(labels, values)}


def check_collection_properties(properties):
    labels = ['n_files', 'n_folders', 'breadth_max', 'breadth_mean', 'root_n_folders', 'n_leaf_folders',
              'pct_leaf_folders', 'depth_leaf_folders_mean', 'n_switch_folders', 'pct_switch_folders',
              'depth_switch_folders_mean', 'depth_max', 'depth_folders_mode', 'depth_folders_mean',
              'branching_factor', 'root_n_files', 'n_files_mean', 'n_empty_folders', 'pct_empty_folders',
              'depth_files_mean', 'depth_files_mode', 'file_breadth_mode_n_files']
    typical_ranges = {'n_files': [29123, 193001],
                      'n_folders': [3818, 26363],
                      'breadth_max': [947, 4990],
                      'breadth_mean': [290, 888],
                      'root_n_folders': [15, 18],
                      'n_leaf_folders': [2582, 18192],
                      'pct_leaf_folders': [66, 80],
                      'depth_leaf_folders_mean': [5.2, 8.8],
                      'n_switch_folders': [591, 4291],
                      'pct_switch_folders': [9, 23],
                      'depth_switch_folders_mean': [4.75, 8.25],
                      'depth_max': [12, 18],
                      'depth_folders_mode': [5, 7],
                      'depth_folders_mean': [6, 8],
                      'branching_factor': [3, 4.5],
                      'root_n_files': [properties['n_roots']*x for x in [4, 8]],
                      'n_files_mean': [6, 8],
                      'n_empty_folders': [304, 3057],
                      'pct_empty_folders': [5, 12],
                      'depth_files_mean': [5, 8],
                      'depth_files_mode': [4, 4],
                      'file_breadth_mode_n_files': [9892, 52230]}
    is_typical_dict = dict(zip(labels, [True]*len(labels)))
    diff_dict = dict(zip(labels, [None]*len(labels)))
    for label in labels:
        if properties[label] is not None:
            if properties[label] < typical_ranges[label][0]:
                is_typical_dict[label] = False
                diff_dict[label] = properties[label] - typical_ranges[label][0]
            elif properties[label] > typical_ranges[label][1]:
                is_typical_dict[label] = False
                diff_dict[label] = properties[label] - typical_ranges[label][1]
        else:
            diff_dict[label] = None
        # print(label, properties[label], diff_dict[label])
    return all(is_typical_dict.values()), typical_ranges, diff_dict


if __name__ == "__main__":
    root_path = os.path.expanduser(os.path.join('~', 'Dropbox'))
    # root_path = os.path.expanduser(os.path.join('~', 'Downloads'))
    test_dir_dict = record_stat(root_path)
    test_dir_dict = compute_stat(test_dir_dict)
    anonymize_stat(test_dir_dict, [1])
    test_dir_dict = record_stat(root_path)
    test_dir_dict = compute_stat(test_dir_dict)
    with open(os.path.expanduser(os.path.join('~', 'Dropbox', 'mcgill', 'File Zoomer',
                                              'code', 'drive_analysis_tool', 'dir_dict.pkl')), 'wb') as ddf:
        pickle.dump(test_dir_dict, ddf, pickle.HIGHEST_PROTOCOL)
    # with open(os.path.expanduser(os.path.join('~', 'Dropbox', 'mcgill', 'File Zoomer',
    #                                           'code', 'drive_analysis_tool', 'dir_dict.pkl')), 'rb') as ddf:
    #     dir_dict = pickle.load(ddf)
    print(test_dir_dict[1])
    # assign_folder_depth(1, test_dir_dict)
    test_dir_dict_props = drive_measurement(test_dir_dict)
    print(test_dir_dict_props)
    print(check_collection_properties(test_dir_dict_props))
    depths_list = [test_dir_dict[key]['depth'] for key in test_dir_dict.keys()]
    print(Counter(depths_list))
