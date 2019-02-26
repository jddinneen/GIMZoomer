import os
import json
import csv
import lzma
from pathlib import Path
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.fernet import Fernet
from private_key import load_private_key
from drive_analyzer import drive_measurement, check_collection_properties


def decrypt_data(json_filepath, jsonkey_filepath, privatekey_filepath):
    privatekey = load_private_key(privatekey_filepath)

    # Decrypt Fernet key, then use Fernet key to decrypt dict
    with open(jsonkey_filepath, 'rb') as jsonkey_file:
        jsonkey = privatekey.decrypt(jsonkey_file.read(), padding=padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None))
    jsonkey_f = Fernet(jsonkey)
    with open(json_filepath, 'rb') as json_file:
        dir_dict_json = jsonkey_f.decrypt(json_file.read())
    dir_dict_json = decompress_data(dir_dict_json)
    dir_dict = json.loads(dir_dict_json)

    # Converts all keys from strs to ints
    # (they were turned to strs when going from dict to json)
    for key in sorted(dir_dict.keys()):
        dir_dict[int(key)] = dir_dict[key]
        dir_dict.pop(key)

    return dir_dict


def decompress_data(bytes_data):
    return lzma.decompress(bytes_data)


def list_encoded_files(dirpath):
    filelist = []
    userlist = []
    jsonkeydict = dict()
    for filename in os.listdir(dirpath):
        # Does not handle cases where filename contains multiple '.'
        name, ext = filename.split('.')
        if ext == 'enc':
            user_id = name.split('_')[0]
            full_filepath = os.path.join(dirpath, filename)
            if name.endswith('sym_key'):
                jsonkeydict[user_id] = full_filepath
            else:
                userlist.append(user_id)
                filelist.append(full_filepath)
    return userlist, filelist, jsonkeydict


def decrypt_files(userlist, filelist, jsonkeydict, privatekey_filepath):
    decrypted_dirdicts = dict()
    user_rootcount = dict()
    # Assuming that userlist and filelist are of equal length
    for user_id, json_filepath in zip(userlist, filelist):
        if user_id not in user_rootcount.keys():
            user_rootcount[user_id] = 1
            decrypted_dirdicts[user_id] = {}
        else:
            user_rootcount[user_id] += 1
        root_ix = user_rootcount[user_id]
        decrypted_dirdicts[user_id][root_ix] = decrypt_data(
            json_filepath, jsonkeydict[user_id], privatekey_filepath)
    return decrypted_dirdicts


def calculate_props(decrypted_dirdicts):
    props_dict = dict()
    for user_id in decrypted_dirdicts.keys():
        props_dict[user_id] = {}
        for root_ix in decrypted_dirdicts[user_id].keys():
            measurements = drive_measurement([decrypted_dirdicts[user_id][root_ix]], allow_stat_error=True)
            _, typical_ranges, diff_dict = check_collection_properties(measurements)
            props = list(typical_ranges.keys())
            vmmd_dict = {prop: {'value': measurements[prop],
                                'min': typical_ranges[prop][0],
                                'max': typical_ranges[prop][1],
                                'diff': diff_dict[prop]} for prop in props}
            props_dict[user_id][root_ix] = vmmd_dict
    return props_dict


def all_responses_to_csv(props_dict, csv_filepath):
    with open(csv_filepath, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['user (or session id)', 'root1-4', 'property',
                    'value', 'min', 'max', 'diff'])
        vmmd_keys = ['value', 'min', 'max', 'diff']
        for user in props_dict.keys():
            for ix in props_dict[user].keys():
                for prop in props_dict[user][ix].keys():
                    w.writerow([user, ix, prop] +
                               [props_dict[user][ix][prop][x] for x in vmmd_keys])


if __name__ == '__main__':
    # # Define filepaths
    # test_private_key_filepath = os.path.expanduser(os.path.join('~', 'Dropbox', 'mcgill',
    #                                                        'File Zoomer', 'private_key.pem'))
    # # test_json_filepath = os.path.expanduser(os.path.join('~', 'Dropbox', 'mcgill', 'File Zoomer',
    # #                                           'code', 'drive_analysis_tool', 'dir_dict.enc'))
    # # test_jsonkey_filepath = os.path.expanduser(os.path.join('~', 'Dropbox', 'mcgill', 'File Zoomer',
    # #                                           'code', 'drive_analysis_tool', 'sym_key.enc'))
    # test_json_filepath_1 = os.path.expanduser(os.path.join('~', 'Dropbox', 'Apps', 'drive analysis results',
    #                                                        'naW7JONQBCuu7VDG_20190201_170937_dir_dict_1.enc'))
    # test_json_filepath_2 = os.path.expanduser(os.path.join('~', 'Dropbox', 'Apps', 'drive analysis results',
    #                                                        'naW7JONQBCuu7VDG_20190201_170937_dir_dict_2.enc'))
    # test_json_filepath_3 = os.path.expanduser(os.path.join('~', 'Dropbox', 'Apps', 'drive analysis results',
    #                                                        'naW7JONQBCuu7VDG_20190201_170937_dir_dict_3.enc'))
    # test_json_filepath_4 = os.path.expanduser(os.path.join('~', 'Dropbox', 'Apps', 'drive analysis results',
    #                                                        'naW7JONQBCuu7VDG_20190201_170937_dir_dict_4.enc'))
    # test_jsonkey_filepath = os.path.expanduser(os.path.join('~', 'Dropbox', 'Apps', 'drive analysis results',
    #                                                         'naW7JONQBCuu7VDG_20190201_170937_sym_key.enc'))
    #
    # test_dir_dict_1 = decrypt_data(test_json_filepath_1, test_jsonkey_filepath, test_private_key_filepath)
    # print(test_dir_dict_1[sorted(test_dir_dict_1.keys())[1]])
    # print(test_dir_dict_1[sorted(test_dir_dict_1.keys())[2]])
    # test_dir_dict_2 = decrypt_data(test_json_filepath_2, test_jsonkey_filepath, test_private_key_filepath)
    # print(test_dir_dict_2[sorted(test_dir_dict_2.keys())[1]])
    # print(test_dir_dict_2[sorted(test_dir_dict_2.keys())[2]])
    # test_dir_dict_3 = decrypt_data(test_json_filepath_3, test_jsonkey_filepath, test_private_key_filepath)
    # print(test_dir_dict_3[sorted(test_dir_dict_3.keys())[1]])
    # print(test_dir_dict_3[sorted(test_dir_dict_3.keys())[2]])
    # test_dir_dict_4 = decrypt_data(test_json_filepath_4, test_jsonkey_filepath, test_private_key_filepath)
    # print(test_dir_dict_4[sorted(test_dir_dict_4.keys())[1]])
    # print(test_dir_dict_4[sorted(test_dir_dict_4.keys())[2]])
    #
    # print('')
    # test_json_filepath_1 = os.path.expanduser(os.path.join('~', 'Dropbox', 'Apps', 'drive analysis results',
    #                                                        'naW7JONQBCuu7VDG_20190201_170937_dir_dict_1.enc'))
    # test_json_filepath_2 = os.path.expanduser(os.path.join('~', 'Dropbox', 'Apps', 'drive analysis results',
    #                                                        'naW7JONQBCuu7VDG_20190201_170937_dir_dict_2.enc'))
    # test_jsonkey_filepath = os.path.expanduser(os.path.join('~', 'Dropbox', 'Apps', 'drive analysis results',
    #                                                         'naW7JONQBCuu7VDG_20190201_170937_sym_key.enc'))
    # test_dir_dict_1 = decrypt_data(test_json_filepath_1, test_jsonkey_filepath, test_private_key_filepath)
    # print(test_dir_dict_1[sorted(test_dir_dict_1.keys())[1]])
    # print(test_dir_dict_1[sorted(test_dir_dict_1.keys())[2]])
    # test_dir_dict_2 = decrypt_data(test_json_filepath_2, test_jsonkey_filepath, test_private_key_filepath)
    # print(test_dir_dict_2[sorted(test_dir_dict_2.keys())[1]])
    # print(test_dir_dict_2[sorted(test_dir_dict_2.keys())[2]])

    # Define paths to files and folders
    test_privatekey_filepath = str(Path(
        '~/Dropbox/mcgill/File Zoomer/private_key.pem').expanduser())
    test_dirpath = str(Path(
        '~/Dropbox/Apps/drive analysis results').expanduser())
    test_csv_filepath = str(Path(
        '~/Dropbox/Apps/drive analysis results/folder_props.csv').expanduser())
    # Convert collected jsons to a single csv file
    test_userlist, test_filelist, test_jsonkeydict = list_encoded_files(test_dirpath)
    test_decrypted_dirdicts = decrypt_files(
        test_userlist, test_filelist,
        test_jsonkeydict, test_privatekey_filepath)
    test_props_dict = calculate_props(test_decrypted_dirdicts)
    all_responses_to_csv(test_props_dict, test_csv_filepath)
