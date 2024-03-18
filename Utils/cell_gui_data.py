import os.path
import pandas as pd

from Utils.gui_generate import generate_cell_wise_gui_data, generate_fate_wise_from_cell_wise_gui_data
from Utils.gui_data_io import move_file


def cell_gui_data(base_path, selected_embryo, selected_model, output_path):
    is_generate_cell_wise_gui_data = True  # depulicate all raw images and segmented files for ITK-SNAP-CVE software
    is_generate_fate_wise_gui_data = True  # depulicate all raw images and segmented files for ITK-SNAP-CVE software

    # =====================calculate volume surface contact=====================================
    embryo_names = [selected_embryo]
    stat_data_folder = os.path.join(output_path, 'Statistics')
    cell_fate_dictionary = os.path.join(base_path, 'CellFate.xls')
    name_dictionary_path = os.path.join(base_path, 'name_dictionary.csv')
    # by user
    #save_cell_wise_gui_folder = r'E:\NucleiSegmentation\CellAppData\testing_cell_wise_gui'
    save_cell_wise_gui_folder = os.path.join(output_path, 'testing_cell_wise_gui')
    move_file(name_dictionary_path, save_cell_wise_gui_folder + "/name_dictionary.csv")

    label_name_dict = pd.read_csv(name_dictionary_path, index_col=0).to_dict()['0']
    name_label_dict = {value: key for key, value in label_name_dict.items()}

    if is_generate_cell_wise_gui_data:
        for idx, embryo_name in enumerate(embryo_names):
            raw_image_folder = os.path.join(base_path, 'RawStack', embryo_name, 'RawMemb')
            segmented_unified_folder = os.path.join(base_path, 'SegStack', embryo_name, selected_model,
                                                    'SegCellUnified')

            cd_file_path = os.path.join(base_path, 'CDfiles', '{}.csv'.format(embryo_name))
            generate_cell_wise_gui_data(raw_image_folder, segmented_unified_folder, stat_data_folder,
                                        save_cell_wise_gui_folder, embryo_name, name_dictionary_path, cd_file_path)

    # by user
    to_save_fate_wise_gui_folder = os.path.join(output_path, 'testing_fate_wise_gui')
    # cell_wise_gui_data_folder = r'./middle_output/GUIDataCellWise'
    if not os.path.exists(to_save_fate_wise_gui_folder):
        os.makedirs(to_save_fate_wise_gui_folder)
    if is_generate_fate_wise_gui_data:
        fate_dictionary = {1: 'Death',
                           2: 'GermCell',
                           3: 'Intestin',
                           4: 'Muscle',
                           5: 'Neuron',
                           6: 'Other',
                           7: 'Pharynx',
                           8: 'Skin',
                           9: 'Unspecified'
                           }
        pd_name_dictionary = pd.DataFrame.from_dict(fate_dictionary, orient="index")
        pd_name_dictionary.to_csv(os.path.join(to_save_fate_wise_gui_folder, 'name_dictionary.csv'))
        for idx, embryo_name in enumerate(embryo_names):
            generate_fate_wise_from_cell_wise_gui_data(cell_fate_dictionary, name_dictionary_path,
                                                       save_cell_wise_gui_folder, embryo_name,
                                                       to_save_fate_wise_gui_folder)

