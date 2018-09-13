import os


def read_and_count(root):
    # if len(root) == 1 and os.name == 'posix':
    #     root_parent = ''
    # elif len(root.split(os.sep)) == 1 and os.name == 'nt':
    #     root_parent = root  # this doesn't solve the problem of invalid dirpath like C:\C:
    # else:
    #     root_parent = os.sep.join(root.split(os.sep)[:-1])

    # For each folder, count number of files within and identify its parent
    dir_dict = dict()
    order_dict = dict()
    dirorder = 0
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        dirnames[:] = [dir for dir in dirnames if dir[0] != '.']
        filenames[:] = [file for file in filenames if file[0] != '.']
        if dirorder == 0:
            dirparent = ''  # reconstruct path with root_parent + os.sep + dirparent
        else:
            dirparent = os.sep.join(dirpath.split(os.sep)[:-1])
        dir_dict[dirpath] = [dirorder, dirparent, dirnames, filenames, len(filenames), []]
        order_dict[dirorder] = dirpath
        dirorder += 1

    # Track which sibling group a node belongs to
    for i in sorted(order_dict.keys()):
        dirpath = order_dict[i]
        children = dir_dict[dirpath][2]
        for child in children:
            dir_dict[dirpath + os.sep + child][5] = children

    # Count cumulative accessible files
    for i in range(len(dir_dict))[::-1]:
        dirpath = order_dict[i]
        children = dir_dict[dirpath][2]
        if len(children) > 0:
            dir_dict[dirpath][4] += sum([dir_dict[dirpath + os.sep + child][4] for child in children])

    print('nfiles path')
    for i in range(len(dir_dict)):
        dirpath = order_dict[i]
        print('%6s' % str(dir_dict[dirpath][4]) + ' ' + dirpath)

    return dir_dict, order_dict  # root_parent


def compress(dirpath, dir_dict, order_dict, threshold_compr=0.95):
    children = dir_dict[dirpath][2]
    accfiles = float(dir_dict[dirpath][4])
    try:
        passed_threshold = sum([dir_dict[dirpath + os.sep + child][4]/accfiles > threshold_compr for child in children]) > 0
        if passed_threshold:
            new_parent = dir_dict[dirpath][1]
            new_siblings = list(set([dirpath.split(os.sep)[-1]] + dir_dict[dirpath][5])) + children
            children_accfiles = 0
            for child in children:
                new_childpath = os.sep.join(dirpath.split(os.sep)[:-1]) + os.sep + child
                dir_dict[new_childpath] = dir_dict.pop(dirpath + os.sep + child)  # change child's key
                dir_dict[new_childpath][1] = new_parent  # change child's parent
                dir_dict[new_childpath][5] = new_siblings
                order_dict[dir_dict[new_childpath][0]] = new_childpath
                children_accfiles += dir_dict[new_childpath][4]
            dir_dict[dirpath][2] = []  # remove children from current dirpath
            dir_dict[dirpath][4] -= children_accfiles
            dir_dict[dirpath][5] = new_siblings
    except ZeroDivisionError:  # catches the case of empty parent with empty children
        for child in children:
            childpath = dirpath + os.sep + child
            order_dict.pop(dir_dict[childpath][0])
            dir_dict.pop(childpath)
        order_dict.pop(dir_dict[dirpath][0])
        dir_dict.pop(dirpath)
    # if children are shifted up, how will you deal with pruning??? Keep track of siblings?
    return dir_dict, order_dict


# Pruning done when node is sibling. Perhaps consider pruning children as a parent
# (since paper suggests min tree depth is two levels deep)
def prune(dirpath, dir_dict, order_dict, threshold_prune=0.02):
    try:
        parent_dirpath = dir_dict[dirpath][1]
        parent_accfiles = float(dir_dict[parent_dirpath][4])
        if parent_accfiles != 0:  # catches the case of empty parent with empty children
            siblings = dir_dict[dirpath][5]
            siblings_accfiles = dict(zip(siblings, [dir_dict[parent_dirpath + os.sep + sib][4] for sib in siblings]))
            siblings = sorted(siblings_accfiles, key=siblings_accfiles.__getitem__, reverse=True)

            # this while loop tests the first sorted sibling instead of starting at the second sorted sibling
            # j = 0
            # passed_threshold = False
            # dom_siblings = []
            # while not passed_threshold and j < len(siblings) - 1:
            #     ratio = dir_dict[parent_dirpath + os.sep + siblings[j]][4]/parent_accfiles
            #     if ratio < threshold_prune:
            #         passed_threshold = True
            #     else:
            #         dom_siblings.append(siblings[j])
            #         j += 1

            # this while loop behaves differently but matches the paper's algorithm description closer, I think
            j = 0
            ratio = 1
            dom_siblings = []
            while not ratio < threshold_prune and j < len(siblings) - 1:
                dom_siblings.append(siblings[j])
                j += 1
                ratio = dir_dict[parent_dirpath + os.sep + siblings[j]][4]/parent_accfiles
            pruned_siblings = set(siblings).difference(set(dom_siblings))
            pruned_sib_accfiles = 0
            for sib in pruned_siblings:
                sibpath = parent_dirpath + os.sep + sib
                pruned_sib_accfiles += pruned_sib_accfiles
                order_dict.pop(dir_dict[sibpath][0])
                dir_dict.pop(sibpath)
            for sib in dom_siblings:
                dir_dict[parent_dirpath + os.sep + sib][5] = dom_siblings
            dir_dict[parent_dirpath][2] = dom_siblings  # change parent's children to dominant siblings
            dir_dict[parent_dirpath][4] -= pruned_sib_accfiles
        elif parent_accfiles == 0:
            pass  # should nodes without any accessible files be deleted?
    except KeyError:
        pass  # if node has no parent (root), skip pruning
    return dir_dict, order_dict


def prune_old(dirpath, root_parent, dir_dict, order_dict, threshold_prune=0.02):
    # use median or mean ratios, or find the ratio of the child with max accfile
    # If root node is compressed, how can I prune since I my recursion begins at root and not root_parent???
    children = dir_dict[dirpath][2]
    children_accfiles = dict(zip(dir_dict[dirpath][2], [dir_dict[dirpath + os.sep + child][4] for child in children]))
    children = sorted(children_accfiles, key=children_accfiles.__getitem__, reverse=True)
    j = 0
    passed_threshold = False
    dom_children = []
    while not passed_threshold and j < len(children) - 1:
        ratio = dir_dict[dirpath + os.sep + children[j]][4]/dir_dict[dirpath][4]
        if ratio < threshold_prune:
            passed_threshold = True
        else:
            dom_children.append(children[j])
            j += 1
    pruned_children = set(children).difference(set(dom_children))
    for child in pruned_children:
        dir_dict.pop(dirpath + os.sep + child)
    dir_dict[dirpath][2] = dom_children
    return dir_dict


def simplify(dir_dict, order_dict, threshold_compr, threshold_prune):
    # find the next un-popped node on order_dict
    for i in sorted(order_dict.keys()):
        try:
            dirpath = order_dict[i]
            dir_dict, order_dict = compress(dirpath, dir_dict, order_dict, threshold_compr)
            dir_dict, order_dict = prune(dirpath, dir_dict, order_dict, threshold_prune)
        except KeyError:
            pass
    return dir_dict, order_dict


def simplify_tree(dir_dict, order_dict, threshold_compr=0.95, threshold_prune=0.02):
    while True:
        old_dir_dict, old_order_dict = dir_dict.copy(), order_dict.copy()
        dir_dict, order_dict = simplify(dir_dict, order_dict, threshold_compr, threshold_prune)
        print('nfiles path')
        for i in sorted(order_dict.keys()):
            dirpath = order_dict[i]
            print('%6s' % str(dir_dict[dirpath][4]) + ' ' + dirpath)
        print('\n')
        if old_dir_dict == dir_dict:
            break
    return dir_dict, order_dict


def main():
    # dirpath = 'C:\\Users\\ultra\\Dropbox\\mcgill\\2017 Fall'
    # root = '/Users/huhwhat/Dropbox/mcgill'
    # root = '/Users/huhwhat/Documents/filecount_test'
    root = 'C:\\Users\\ultra\\Dropbox\\mcgill\\'
    # root = raw_input("Enter directory path:")
    if root[-1] == os.sep:
        root = root[:-1]

    dir_dict, order_dict = read_and_count(root)
    # dir_dict_copy = dir_dict.copy()
    # order_dict_copy = order_dict.copy()
    dir_dict, order_dict = simplify_tree(dir_dict, order_dict)
    # print('nfiles path')
    # for i in sorted(order_dict.keys()):
    #     dirpath = order_dict[i]
    #     print('%6s' % str(dir_dict[dirpath][4]) + ' ' + dirpath)

    raw_input("Press Enter to quit.")


if __name__ == "__main__":
    main()
