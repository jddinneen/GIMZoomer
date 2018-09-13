import os


def main():
    # root = '/Users/huhwhat/Dropbox/mcgill'
    # root = '/Users/huhwhat/Documents/filecount_test'
    root = raw_input("Enter directory path:")

    root_tree = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        dirnames[:] = [dir for dir in dirnames if dir[0] != '.']
        filenames[:] = [file for file in filenames if file[0] != '.']
        root_tree.append((dirpath, dirnames, filenames, len(filenames)))

    all_cumcount = dict([(dirpath, n_files) for dirpath, dirnames, filenames, n_files in root_tree])
    all_children = dict([(dirpath, dirnames) for dirpath, dirnames, filenames, n_files in root_tree])
    for dirpath, dirnames, filenames, n_files in root_tree[::-1]:
        children = all_children[dirpath]
        if len(children) > 0:
            all_cumcount[dirpath] += sum([all_cumcount[dirpath + os.sep + child] for child in children])

    print('nfiles path')
    for dirpath, dirnames, filenames, n_files in root_tree:
        print('%6s' % str(all_cumcount[dirpath]) + ' ' + dirpath)

    raw_input("Press Enter to quit.")


if __name__ == "__main__":
    main()
