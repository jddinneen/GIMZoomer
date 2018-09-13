import os


def read_and_count():
    # root = '/Users/huhwhat/Dropbox/mcgill'
    # root = '/Users/huhwhat/Documents/filecount_test'
    # root = 'C:\\Users\\ultra\\Dropbox\\mcgill\\'
    root = raw_input("Enter directory path:")
    if root[-1] == os.sep:
        root = root[:-1]

    root_tree = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        dirnames[:] = [dir for dir in dirnames if dir[0] != '.']
        filenames[:] = [file for file in filenames if file[0] != '.']
        root_tree.append((dirpath, dirnames, filenames, len(filenames), dirpath.split(os.sep)[-2]))

    all_cumcount_children = dict([(dirpath, [n_files, dirnames]) for dirpath, dirnames, filenames, n_files, dirparent in root_tree])
    for dirpath, dirnames, filenames, n_files, dirparent in root_tree[::-1]:
        children = all_cumcount_children[dirpath][1]
        if len(children) > 0:
            all_cumcount_children[dirpath][0] += sum([all_cumcount_children[dirpath + os.sep + child][0] for child in children])

    print('nfiles path')
    for dirpath, dirnames, filenames, n_files, dirparent in root_tree:
        print('%6s' % str(all_cumcount_children[dirpath][0]) + ' ' + dirpath)

    return root_tree, all_cumcount_children
    # raw_input("Press Enter to quit.")


def compress(dirpath, root_tree, all_cumcount_children, threshold_compr):
    # if compress threshold met, then for all children, your parent becomes their parents,
    # then delist them as your children since you're their sibling now

    def remove_parent(dirpath, parent_pos, all_cumcount_children):
        for child in all_cumcount_children[dirpath][1]:
            remove_parent(dirpath + os.sep + child, parent_pos, all_cumcount_children)
        dirpath_decomposed = dirpath.split(os.sep)
        dirpath_decomposed.pop(parent_pos)
        dirpath_new = os.sep.join(dirpath_decomposed)
        all_cumcount_children[dirpath_new] = all_cumcount_children.pop(dirpath)
        print(dirpath, dirpath_new, all_cumcount_children[dirpath_new])
        return all_cumcount_children

    children, cumcount = all_cumcount_children[dirpath]
    cumcount = float(cumcount)
    threshold_passed = sum([(all_cumcount_children[dirpath + os.sep + child] / cumcount) > threshold_compr for child in children]) > 0
    if threshold_passed:
        # for all children duplicate key-value pair but change key to compressed path, then remove old key-value pair
        parent_pos = len(dirpath.split(os.sep)) - 1
        all_cumcount_children = remove_parent(dirpath, parent_pos, all_cumcount_children)
        all_cumcount_children[dirpath] = all_cumcount_children.pop(os.sep.join(dirpath.split(os.sep)[:-1]))  # since remove_parent removes the node itself, this fixes it
        all_cumcount_children[dirpath][0] -= sum([all_cumcount_children[dirpath + os.sep + child][0] for child in all_cumcount_children[dirpath][1]])  # since children are gone, number of accessible fiels drop
        all_cumcount_children[dirpath][1] = []  # since parent is removed, the node itself no longer has children
    return all_cumcount_children


def prune():
    pass


def main():
    root_tree, all_cumcount_children = read_and_count()
    threshold_compr = 0.95
    threshold_prune = 0.95
    for dirpath, dirnames, filenames, n_files, dirparent in root_tree:
        pass
    pass


if __name__ == "__main__":
    main()
