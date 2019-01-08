import os
import json
import lzma
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.fernet import Fernet
from private_key import load_private_key


def decrypt_data(json_filepath, jsonkey_filepath, private_key_filepath):
    private_key = load_private_key(private_key_filepath)

    # Decrypt Fernet key, then use Fernet key to decrypt dict
    with open(jsonkey_filepath, 'rb') as jsonkey_file:
        jsonkey = private_key.decrypt(jsonkey_file.read(), padding=padding.OAEP(
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


if __name__ == '__main__':
    # Define filepaths
    test_private_key_filepath = os.path.expanduser(os.path.join('~', 'Dropbox', 'mcgill',
                                                           'File Zoomer', 'private_key.pem'))
    # test_json_filepath = os.path.expanduser(os.path.join('~', 'Dropbox', 'mcgill', 'File Zoomer',
    #                                           'code', 'drive_analysis_tool', 'dir_dict.enc'))
    # test_jsonkey_filepath = os.path.expanduser(os.path.join('~', 'Dropbox', 'mcgill', 'File Zoomer',
    #                                           'code', 'drive_analysis_tool', 'sym_key.enc'))
    test_json_filepath_1 = os.path.expanduser(os.path.join('~', 'Dropbox', 'Apps', 'Drive Analysis Tool',
                                                           'g8kwGlNY9G1X4eOX_20190108_080730_dir_dict_1.enc'))
    test_json_filepath_2 = os.path.expanduser(os.path.join('~', 'Dropbox', 'Apps', 'Drive Analysis Tool',
                                                           'g8kwGlNY9G1X4eOX_20190108_080730_dir_dict_2.enc'))
    test_json_filepath_3 = os.path.expanduser(os.path.join('~', 'Dropbox', 'Apps', 'Drive Analysis Tool',
                                                           'g8kwGlNY9G1X4eOX_20190108_080730_dir_dict_3.enc'))
    test_json_filepath_4 = os.path.expanduser(os.path.join('~', 'Dropbox', 'Apps', 'Drive Analysis Tool',
                                                           'g8kwGlNY9G1X4eOX_20190108_080730_dir_dict_4.enc'))
    test_jsonkey_filepath = os.path.expanduser(os.path.join('~', 'Dropbox', 'Apps', 'Drive Analysis Tool',
                                                            'g8kwGlNY9G1X4eOX_20190108_080730_sym_key.enc'))

    test_dir_dict_1 = decrypt_data(test_json_filepath_1, test_jsonkey_filepath, test_private_key_filepath)
    print(test_dir_dict_1[sorted(test_dir_dict_1.keys())[1]])
    print(test_dir_dict_1[sorted(test_dir_dict_1.keys())[2]])
    test_dir_dict_2 = decrypt_data(test_json_filepath_2, test_jsonkey_filepath, test_private_key_filepath)
    print(test_dir_dict_2[sorted(test_dir_dict_2.keys())[1]])
    print(test_dir_dict_2[sorted(test_dir_dict_2.keys())[2]])
    test_dir_dict_3 = decrypt_data(test_json_filepath_3, test_jsonkey_filepath, test_private_key_filepath)
    print(test_dir_dict_3[sorted(test_dir_dict_3.keys())[1]])
    print(test_dir_dict_3[sorted(test_dir_dict_3.keys())[2]])
    test_dir_dict_4 = decrypt_data(test_json_filepath_4, test_jsonkey_filepath, test_private_key_filepath)
    print(test_dir_dict_4[sorted(test_dir_dict_4.keys())[1]])
    print(test_dir_dict_4[sorted(test_dir_dict_4.keys())[2]])

    print('')
    test_json_filepath_1 = os.path.expanduser(os.path.join('~', 'Dropbox', 'Apps', 'Drive Analysis Tool',
                                                           'ZrhSRNNdqrlHZWv1_20190108_102814_dir_dict_1.enc'))
    test_json_filepath_2 = os.path.expanduser(os.path.join('~', 'Dropbox', 'Apps', 'Drive Analysis Tool',
                                                           'ZrhSRNNdqrlHZWv1_20190108_102814_dir_dict_2.enc'))
    test_jsonkey_filepath = os.path.expanduser(os.path.join('~', 'Dropbox', 'Apps', 'Drive Analysis Tool',
                                                            'ZrhSRNNdqrlHZWv1_20190108_102814_sym_key.enc'))
    test_dir_dict_1 = decrypt_data(test_json_filepath_1, test_jsonkey_filepath, test_private_key_filepath)
    print(test_dir_dict_1[sorted(test_dir_dict_1.keys())[1]])
    print(test_dir_dict_1[sorted(test_dir_dict_1.keys())[2]])
    test_dir_dict_2 = decrypt_data(test_json_filepath_2, test_jsonkey_filepath, test_private_key_filepath)
    print(test_dir_dict_2[sorted(test_dir_dict_2.keys())[1]])
    print(test_dir_dict_2[sorted(test_dir_dict_2.keys())[2]])

