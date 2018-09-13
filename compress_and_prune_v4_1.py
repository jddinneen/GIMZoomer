import os
import math


def read_and_count(root):
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


def print_tree(root, dir_dict):
    print('nfiles path')
    for dirkey in sorted(dir_dict.keys()):
        parent = dir_dict[dirkey][1]
        if parent:
            dirparents = []
            while parent:
                dirparents.append(dir_dict[parent][0])
                parent = dir_dict[parent][1]
            dirparents = dirparents[:-1][::-1]
            if len(dirparents) == 0:
                dirpath = root + os.sep + dir_dict[dirkey][0]
            else:
                dirparents = os.sep.join(dirparents)
                dirpath = os.sep.join([root, dirparents, dir_dict[dirkey][0]])
        else:
            dirpath = root
        print('%6s' % str(dir_dict[dirkey][4]) + ' ' + dirpath)


def find_all_children(dirkey, dir_dict):
    children = []
    for child in dir_dict[dirkey][2]:
        children.extend(find_all_children(child, dir_dict))
    children.extend(dir_dict[dirkey][2])
    return children


def compress(root, dirkey, dir_dict, threshold_compr=0.95, print_=False):
    if not dir_dict[dirkey][1]:  # do not compress the root node
        if print_:
            print('Compressing...')
            print_tree(root, dir_dict)
            print('\n')
        return dir_dict
    else:
        accfiles = float(dir_dict[dirkey][4])  # convert to float so that division produces floats instead of int
        if accfiles > 0:  # only compress node (parent) which has at least one accessible file
            children = dir_dict[dirkey][2]
            passed_threshold = sum([dir_dict[child][4]/accfiles > threshold_compr for child in children]) > 0
            if passed_threshold:
                new_parent = dir_dict[dirkey][1]
                for child in children:
                    dir_dict[child][1] = new_parent
                dir_dict[dirkey][2] = []
                dir_dict[dirkey][4] = len(dir_dict[dirkey][3])
                if new_parent:  # don't forget to get the new parent to recognize its new children
                    new_parent_children_set = set(dir_dict[new_parent][2]).difference(set([dirkey]))
                    new_parent_children_set |= set(children)
                    dir_dict[new_parent][2] = list(new_parent_children_set)
        elif accfiles == 0:  # if no files are accessible (empty parent and empty children), delete nodes
            parent = dir_dict[dirkey][1]
            if parent:
                dir_dict[parent][2] = list(set(dir_dict[parent][2]).difference(set([dirkey])))
            empty_children = find_all_children(dirkey, dir_dict)
            dir_dict.pop(dirkey)
            for child in empty_children:
                dir_dict.pop(child)
        if print_:
            print('Compressing')
            print_tree(root, dir_dict)
            print('\n')
        return dir_dict


def prune(root, dirkey, dir_dict, threshold_prune=0.02, print_=False):
    accfiles = float(dir_dict[dirkey][4])
    children = dir_dict[dirkey][2]
    if accfiles > 0 and len(children) > 0:  # check that parent is not empty and there are children
        children_accfiles = dict(zip(children, [dir_dict[child][4] for child in children]))
        children = sorted(children_accfiles, key=children_accfiles.__getitem__, reverse=True)
        children_accfiles_total = float(sum(children_accfiles.values()))
        dom_siblings = []
        ratio = 1
        j = 0
        while not ratio < threshold_prune and j < len(children):
            dom_siblings.append(children[j])
            j += 1
            if j < len(children):
                try:
                    ratio = dir_dict[children[j]][4] / children_accfiles_total
                except ZeroDivisionError:
                    ratio = math.inf
                    # print(dir_dict[children[j]][4], children_accfiles_total)
        pruned_siblings = list(set(children).difference(dom_siblings))
        pruned_nodes = []  # to prune children of pruned siblings
        pruned_sib_accfiles = 0
        for sib in pruned_siblings:
            pruned_nodes.extend(find_all_children(sib, dir_dict))
            pruned_sib_accfiles += dir_dict[sib][4]
        pruned_nodes.extend(pruned_siblings)
        for node in pruned_nodes:
            dir_dict.pop(node)
        dir_dict[dirkey][2] = dom_siblings
        parent = dirkey
        while parent:
            dir_dict[parent][4] -= pruned_sib_accfiles
            parent = dir_dict[parent][1]
    elif accfiles == 0:
        parent = dir_dict[dirkey][1]
        if parent:
            dir_dict[parent][2] = list(set(dir_dict[parent][2]).difference(set([dirkey])))
        empty_children = find_all_children(dirkey, dir_dict)
        dir_dict.pop(dirkey)
        for child in empty_children:
            dir_dict.pop(child)

    if print_:
        print('Pruning...')
        print_tree(root, dir_dict)
        print('\n')
    return dir_dict


def simplify(root, dirkey, dir_dict, threshold_compr=0.95, threshold_prune=0.02, print_=False):
    dir_dict = compress(root, dirkey, dir_dict, threshold_compr, print_)
    dir_dict = prune(root, dirkey, dir_dict, threshold_prune, print_)
    for child in dir_dict[dirkey][2]:
        try:
            dir_dict = simplify(root, child, dir_dict, threshold_compr, threshold_prune, print_)
        except KeyError:
            pass
    return dir_dict


def simplify_tree(root, dirkey, dir_dict, threshold_compr=0.95, threshold_prune=0.02, print_=False):
    convergence = False
    npass = 1
    while not convergence:
        # print('Pass: ' + str(npass))
        old_dir_dict = dir_dict.copy()
        dir_dict = simplify(root, dirkey, dir_dict, threshold_compr, threshold_prune, print_)
        npass += 1
        if old_dir_dict == dir_dict:
            convergence = True
    return dir_dict


def main():
    root = input("Enter directory path:")
    if root[-1] == os.sep:  # remove extraneous separators (\ or /) at the end of a path
        root = root[:-1]

    dir_dict = read_and_count(root)
    print('Initial tree:')
    print_tree(root, dir_dict)
    print('\n\n')
    dir_dict = simplify_tree(root, 1, dir_dict, 0.95, 0.02, print_=False)
    print('Final tree:')
    print_tree(root, dir_dict)
    print('\n')


if __name__ == '__main__':
    main()
