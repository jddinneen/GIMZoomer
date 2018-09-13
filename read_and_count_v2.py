import os


def main():
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
        root_tree.append((dirpath, dirnames, filenames, len(filenames)))

    all_cumcount_children = dict([(dirpath, [n_files, dirnames]) for dirpath, dirnames, filenames, n_files in root_tree])
    for dirpath, dirnames, filenames, n_files in root_tree[::-1]:
        children = all_cumcount_children[dirpath][1]
        if len(children) > 0:
            all_cumcount_children[dirpath][0] += sum([all_cumcount_children[dirpath + os.sep + child][0] for child in children])

    print('nfiles path')
    for dirpath, dirnames, filenames, n_files in root_tree:
        print('%6s' % str(all_cumcount_children[dirpath][0]) + ' ' + dirpath)

    raw_input("Press Enter to quit.")


if __name__ == "__main__":
    main()
