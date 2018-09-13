import os

# root = '/Users/huhwhat/Dropbox'
# root = '/Users/huhwhat/Documents/filecount_test'
root = raw_input("Enter directory path:")

# [dir for dir in os.listdir(root) if os.path.isdir(dir) and dir[0] != '.']  # excludes files and hidden folders/files
# root_tree = [(dirpath, dirnames, filenames) for (dirpath, dirnames, filenames) in os.walk(root)]
# root_tree = [(dirpath,
#               [dir for dir in dirnames if dir[0] != '.'],
#               [file for file in filenames if file[0] != '.'])
#              for (dirpath, dirnames, filenames) in os.walk(root, topdown=False) if dirpath.split('/')[-1][0] != '.']
#
# print(len(root_tree))
# print('\n'.join([x[0] for x in root_tree][:10]))

root_tree = []
for dirpath, dirnames, filenames in os.walk(root, topdown=True):
    dirnames[:] = [dir for dir in dirnames if dir[0] != '.']
    filenames[:] = [file for file in filenames if file[0] != '.']
    root_tree.append((dirpath, dirnames, filenames))

# print(len(root_tree))
# print('\n'.join([x[0] for x in root_tree][:10]))
# print('\n'.join(['\n'.join(x[1]) for x in root_tree][:10]))
# print('\n'.join(['\n'.join(x[2]) for x in root_tree][:10]))
# print('\n'.join([x[0] for x in root_tree][-10:]))
# print('\n'.join(['\n'.join(x[1]) for x in root_tree][-10:]))
# print('\n'.join(['\n'.join(x[2]) for x in root_tree][-10:]))

filecounts = [(dirpath, len(dirpath.split(os.sep)), len(filenames)) for dirpath, dirnames, filenames in root_tree]

cumcounts = []
cumcount = 0
old_dirlen = -1
for dirpath, dirlen, filecount in filecounts[::-1]:
    if dirlen < old_dirlen:  # indicates that we have moved up a level (closer to root)
        cumcount += filecount
        cumcounts.append(cumcount)
    elif dirlen == old_dirlen:  # indicates that we have stayed at the same level
        cumcount += filecount
        cumcounts.append(filecount)
    elif dirlen > old_dirlen:  # indicates that we have moved down a level (further from root)
        cumcount = filecount
        cumcounts.append(cumcount)
    old_dirlen = dirlen
cumcounts = cumcounts[::-1]

root_cumcount = filecounts[0][1]
for dirlen, cumcount in zip([x[1] for x in filecounts], cumcounts):
    if dirlen == filecounts[0][1] + 1:
        root_cumcount += cumcount
cumcounts[0] = root_cumcount

# print('\n'.join([x[0] for x in root_tree][:10]))
# print(cumcounts[:10])
print('\n'.join([', '.join(row) for row in zip([x[0] for x in root_tree], [str(x) for x in cumcounts])]))
