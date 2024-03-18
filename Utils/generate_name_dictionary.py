'''
This llibrary defines all structures that will be used in the shape analysis
'''

import os
import glob
import pandas as pd
from treelib import Tree

from .label_data_structure import read_cd_file

def add_number_dict(nucleus_file, save_name_dictionary, max_time):
    '''
    Construct cell tree structure with cell names
    :param nucleus_file:  the name list file to the tree initilization
    :param max_time: the maximum time point to be considered
    :return cell_tree: cell tree structure where each time corresponds to one cell (with specific name)
    '''


    try:
        label_name_dict = pd.read_csv(save_name_dictionary, index_col=0).to_dict()['0']
        name_label_dict = {value: key for key, value in label_name_dict.items()}

    except:
        name_label_dict = {}

    # =====================================
    # dynamic update the name dictionary
    # =====================================
    cell_in_dictionary = list(name_label_dict.keys())

    ace_pd = read_cd_file(os.path.join(nucleus_file))

    ace_pd = ace_pd[ace_pd.time <= max_time]
    cell_list = list(ace_pd.cell.unique())
    add_cell_list = list(set(cell_list) - set(cell_in_dictionary))
    add_cell_list.sort()

    if len(add_cell_list) > 0:

        add_number_dictionary = dict(zip(add_cell_list, range(len(cell_in_dictionary) + 1, len(cell_in_dictionary) + len(add_cell_list) + 1)))
        # --------save name_label_dict csv-------------
        name_label_dict.update(add_number_dictionary)
        pd_number_dictionary = pd.DataFrame.from_dict(name_label_dict, orient="index")
        pd_number_dictionary.to_csv(save_name_dictionary)

        # -----------save label_name_dict csv
        label_name_dict_saving={value: key for key, value in name_label_dict.items()}
        pd_name_dictionary = pd.DataFrame.from_dict(label_name_dict_saving, orient="index")
        pd_name_dictionary.to_csv(save_name_dictionary)

