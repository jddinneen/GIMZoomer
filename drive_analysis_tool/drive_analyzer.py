import os


def walk_and_stat(root):
    # For each folder, count number of files within and identify its parent
    dir_dict = dict()
    order_dict = dict()
    dirorder = 1  # key starts as 1 since 0 can be interpreted as a boolean False
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        invalid_dirs = []
        for dir in dirnames:
            try:
                os.scandir(os.path.join(dirpath, dir))
            except PermissionError:
                invalid_dirs.append(dir)
        dirnames = list(set(dirnames).difference(set(invalid_dirs)))
        dirnames[:] = [dir for dir in dirnames if dir[0] != '.']
        filenames[:] = [file for file in filenames if file[0] != '.']
        if dirorder == 1:
            dirparent = False  # signifies node as top-level, so it has no parent
        else:
            dirparent = os.path.split(dirpath)[0]
        dir_dict[dirorder] = [os.path.split(dirpath)[1],  # directory name [0]
                              dirparent,  # parent key [1]
                              [os.path.join(dirpath, dir) for dir in dirnames],  # children keys [2]
                              filenames,  # names of files found in directory [3]
                              len(filenames)]  # cumulative count of accessible files [4]
        order_dict[dirpath] = dirorder
        dirorder += 1

    # Refer to each node using a unique key instead of dirpath
    for dirkey in sorted(dir_dict.keys()):
        if dirkey > 1:
            dir_dict[dirkey][1] = order_dict[dir_dict[dirkey][1]]
        dir_dict[dirkey][2] = [order_dict[child] for child in dir_dict[dirkey][2]]

    # Count cumulative accessible files
    for dirkey in sorted(dir_dict.keys(), reverse=True):
        children = dir_dict[dirkey][2]
        dir_dict[dirkey][4] += sum([dir_dict[child][4] for child in children])

    # print_tree(root, dir_dict)
    # print('\n')

    return dir_dict
