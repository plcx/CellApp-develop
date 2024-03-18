import os.path
import skimage.morphology
import numpy as np
import pandas as pd
# from skimage.morphology import ball
from scipy import ndimage
from scipy.ndimage import binary_closing
import multiprocessing as mp
from tqdm import tqdm

from glob import glob


from Utils.match_processLib import line_weight_integral
from Utils.match_lineage_tree import construct_celltree
from Utils.match_data_io import nib_load, nib_save, check_folder

def combine_division_mp(para):
    segmented_cell_file_path = para[0]
    predicted_memb_file_path = para[1]
    annotated_nuc_file_path = para[2]
    cell_tree = para[3]

    # overwrite = para[5]
    name_label_dict = para[4]
    label_name_dict = para[5]

    this_tp = os.path.basename(predicted_memb_file_path).split('_')[1]

    pred_memb_map = nib_load(predicted_memb_file_path)
    seg_bin = (pred_memb_map > 0.93 * pred_memb_map.max()).astype(float)

    annotated_nuc = nib_load(annotated_nuc_file_path)
    # nucleus_marker_footprint = skimage.morphology.ball(7 - int(int(this_tp) / 100))
    # annotated_nuc = ndimage.grey_erosion(annotated_nuc, footprint=nucleus_marker_footprint)
    seg_cell = nib_load(segmented_cell_file_path)

    labels = np.unique(annotated_nuc)[1:].tolist()
    # labels.pop(0)
    processed_labels = []
    output_seg_cell = seg_cell.copy()
    cell_labels = np.unique(seg_cell).tolist()

    for one_label in labels:
        one_times = cell_tree[label_name_dict[one_label]].data.get_time()
        if any(time < int(this_tp) for time in one_times):  # if previous division exist
            continue
        if (one_label in processed_labels):
            continue
        parent_label = cell_tree.parent(label_name_dict[one_label])
        if parent_label is None:
            continue
        another_label = [name_label_dict[a.tag] for a in cell_tree.children(parent_label.tag)]
        another_label.remove(one_label)
        another_label = another_label[0]

        if (one_label not in cell_labels) or (another_label not in cell_labels):
            continue

        locations1 = np.where(annotated_nuc == one_label)
        centre_len_tmp = len(locations1[0]) // 2
        # centre_len_tmp = 0
        x_tmp = locations1[0][centre_len_tmp]
        y_tmp = locations1[1][centre_len_tmp]
        z_tmp = locations1[2][centre_len_tmp]
        x0 = [x_tmp,y_tmp,z_tmp]
        locations2 = np.where(annotated_nuc == another_label)
        centre_len_tmp = len(locations2[0]) // 2
        # centre_len_tmp = 0
        x_tmp = locations2[0][centre_len_tmp]
        y_tmp = locations2[1][centre_len_tmp]
        z_tmp = locations2[2][centre_len_tmp]
        x1 = [x_tmp,y_tmp,z_tmp]
        edge_weight = line_weight_integral(x0=x0, x1=x1, weight_volume=seg_bin)
        if edge_weight == 0:
            mask = np.logical_or(seg_cell == one_label, seg_cell == another_label)
            mask = binary_closing(mask, structure=np.ones((3, 3, 3)))
            output_seg_cell[mask] = name_label_dict[parent_label.tag]
            one_times.remove(int(this_tp))
            another_times = cell_tree[label_name_dict[another_label]].data.get_time()
            another_times.remove(int(this_tp))
            cell_tree[label_name_dict[one_label]].data.set_time(one_times)
            cell_tree[label_name_dict[another_label]].data.set_time(another_times)
        processed_labels += [one_label, another_label]
    #
    # if not overwrite:
    #     seg_save_file = os.path.join("./output", embryo, "SegCellTimeCombined",
    #                                  embryo + "_" + str(t).zfill(3) + "_segCell.nii.gz")
    # else:
    seg_save_file = segmented_cell_file_path
    nib_save(output_seg_cell, seg_save_file)


def running_reassign_cellular_map(para):
    segCellniigzpath = para[0]
    cell_tree_embryo = para[1]
    annotated_niigz_path = para[2]
    embryo_name = para[3]
    cell2fate = para[4]
    label_name_dict = para[5]
    output_saving_path = para[6]

    tp_this_str = os.path.basename(segCellniigzpath).split('_')[1]
    segmented_arr = nib_load(segCellniigzpath).astype(int)

    annotated_nuc_arr = nib_load(annotated_niigz_path).astype(int)
    nucleus_marker_footprint = skimage.morphology.ball(7 - int(int(tp_this_str) / 100))
    annotated_nuc_arr = ndimage.grey_erosion(annotated_nuc_arr, footprint=nucleus_marker_footprint)

    new_cellular_arr = np.zeros(segmented_arr.shape)
    cells_list_this = np.unique(annotated_nuc_arr)[1:]
    mapping_cellular_dict = {}
    dividing_cells = []
    lossing_cells = []

    late_processing_cells = []  # the apoptotic cells should be processed in a biological manner
    # deal with
    for cell_index in cells_list_this:
        this_cell_fate = cell2fate.get(label_name_dict[cell_index], 'Unspecified')
        if this_cell_fate == 'Death':
            late_processing_cells.append(cell_index)
        else:
            locations_cellular = np.where(annotated_nuc_arr == cell_index)
            centre_len_tmp = len(locations_cellular[0]) // 2
            # centre_len_tmp = 0
            x_tmp = locations_cellular[0][centre_len_tmp]
            y_tmp = locations_cellular[1][centre_len_tmp]
            z_tmp = locations_cellular[2][centre_len_tmp]

            segmented_arr_index = int(segmented_arr[x_tmp, y_tmp, z_tmp])

            if segmented_arr_index in mapping_cellular_dict.keys() or segmented_arr_index == 0:
                is_found = False
                assigned_cell_name = label_name_dict.get(mapping_cellular_dict.get(segmented_arr_index, 'ZERO'), 'ZERO')
                this_cell_name = label_name_dict[cell_index]

                IS_ZERO_BACK = False
                if assigned_cell_name == 'ZERO' or segmented_arr_index == 0:
                    IS_ZERO_BACK = True

                if not IS_ZERO_BACK:
                    parent_node_occupied = cell_tree_embryo.parent(assigned_cell_name)
                    parent_node_this = cell_tree_embryo.parent(this_cell_name)

                if not IS_ZERO_BACK and parent_node_this.tag == parent_node_occupied.tag:
                    cell_lifecycle = cell_tree_embryo[this_cell_name].data.get_time()
                    nuc_dividing_reasonable = len(cell_lifecycle) // 4

                    if int(tp_this_str) < cell_lifecycle[nuc_dividing_reasonable]:
                        # print(assigned_cell_name,this_cell_name,parent_node_this)
                        new_cellular_arr[segmented_arr == segmented_arr_index] = int(parent_node_this.data.get_number())
                        mapping_cellular_dict[int(segmented_arr_index)] = int(cell_index)
                        dividing_cells.append(parent_node_this.tag)
                        is_found = True
                else:
                    for searching_x in range(5):
                        for searching_y in range(5):
                            for searching_z in range(5):
                                trying_index1 = segmented_arr[
                                    x_tmp + searching_x, y_tmp + searching_y, z_tmp + searching_z]
                                trying_index2 = segmented_arr[
                                    x_tmp - searching_x, y_tmp - searching_y, z_tmp - searching_z]

                                if trying_index1 != 0 and trying_index1 not in mapping_cellular_dict:
                                    new_cellular_arr[segmented_arr == trying_index1] = cell_index
                                    mapping_cellular_dict[int(trying_index1)] = int(cell_index)
                                    is_found = True
                                    break
                                if trying_index2 != 0 and trying_index2 not in mapping_cellular_dict:
                                    new_cellular_arr[segmented_arr == trying_index2] = cell_index
                                    mapping_cellular_dict[int(trying_index2)] = int(cell_index)
                                    is_found = True
                                    break
                            else:
                                continue
                            break
                        else:
                            continue
                        break

                # conflicting_pairs.append((label_name_dict[mapping_cellular_dict[segmented_arr_index]],
                #                           label_name_dict[cell_index]))
                if not is_found:
                    lossing_cells.append(
                        (label_name_dict[cell_index], cell2fate.get(label_name_dict[cell_index], 'Unspecified')))
            # elif segmented_arr_index == 0:
            #     lossing_cells.append((label_name_dict[cell_index], cell2fate[label_name_dict[cell_index]]))
            else:
                new_cellular_arr[segmented_arr == segmented_arr_index] = int(cell_index)
                mapping_cellular_dict[int(segmented_arr_index)] = int(cell_index)

    for cell_index in late_processing_cells:
        nuc_binary_tmp = (annotated_nuc_arr == cell_index)

        locations_cellular = np.where(nuc_binary_tmp)
        centre_len_tmp = len(locations_cellular[0]) // 2
        # centre_len_tmp = 0
        x_tmp = locations_cellular[0][centre_len_tmp]
        y_tmp = locations_cellular[1][centre_len_tmp]
        z_tmp = locations_cellular[2][centre_len_tmp]

        segmented_arr_index = segmented_arr[x_tmp, y_tmp, z_tmp]

        if segmented_arr_index in mapping_cellular_dict.keys() or segmented_arr_index == 0:
            # if segmented_arr_index!=0:
            nuc_binary_tmp_eroded = skimage.morphology.binary_erosion(nuc_binary_tmp)

            new_cellular_arr[nuc_binary_tmp_eroded] = cell_index
            lossing_cells.append((label_name_dict[cell_index], cell2fate[label_name_dict[cell_index]]))
        else:
            mapping_cellular_dict[segmented_arr_index] = cell_index

    nib_save(new_cellular_arr, output_saving_path)

    middle_material_path = os.path.dirname(os.path.dirname(output_saving_path))
    dict_saving_path = os.path.join(middle_material_path, 'middle_materials', 'mapping',
                                    f'{embryo_name}_{tp_this_str}_mapping_dict.csv')
    check_folder(dict_saving_path)
    pd.DataFrame.from_dict(mapping_cellular_dict, orient='index').to_csv(dict_saving_path)

    if len(dividing_cells) > 0:
        conflicting_pairs_saving_path = os.path.join(middle_material_path, 'middle_materials',
                                                     'dividing',
                                                     f'{embryo_name}_{tp_this_str}_dividing.csv')
        check_folder(conflicting_pairs_saving_path)

        pd.DataFrame(dividing_cells).to_csv(conflicting_pairs_saving_path)
    if len(lossing_cells) > 0:
        lossing_pairs_saving_path = os.path.join(middle_material_path, 'middle_materials',
                                                 'losing',
                                                 f'{embryo_name}_{tp_this_str}_losing.csv')
        check_folder(lossing_pairs_saving_path)

        pd.DataFrame(lossing_cells).to_csv(lossing_pairs_saving_path)



def cell_shape_map(base_path, selected_embryo, selected_model):
    embryo_names = [selected_embryo]
    segmented_root_path = os.path.join(base_path, 'SegStack')
    name_dictionary_path = os.path.join(base_path, 'name_dictionary.csv')
    cell_fate_dictionary = os.path.join(base_path, 'CellFate.xls')
    CDfile_root_path = os.path.join(base_path, 'CDfiles')
    output_saving_middle_path = r'SegCellUnified'

    cell_fate = pd.read_excel(cell_fate_dictionary, names=["Cell", "Fate"], converters={"Cell": str, "Fate": str},
                              header=None)
    cell_fate = cell_fate.applymap(lambda x: x[:-1])
    cell2fate = dict(zip(cell_fate.Cell, cell_fate.Fate))

    label_name_dict = pd.read_csv(name_dictionary_path, index_col=0).to_dict()['0']
    name_label_dict = {value: key for key, value in label_name_dict.items()}

    # mapping_dict = {}

    for embryo_name in embryo_names:
        segmented_cell_paths = sorted(
            glob(os.path.join(segmented_root_path, embryo_name, selected_model, 'SegCell', '*.nii.gz')))

        max_time = len(segmented_cell_paths)
        ace_file = os.path.join(CDfile_root_path, embryo_name + ".csv")  # pixel x y z
        cell_tree_embryo = construct_celltree(ace_file, max_time, name_dictionary_path)

        # ====================assign the nucleus label to every cell=============================
        parameters = []
        unified_path = os.path.join(segmented_root_path, embryo_name, selected_model,
                                    output_saving_middle_path)
        if not os.path.exists(unified_path):
            os.makedirs(unified_path)
        for segmented_cell_file in segmented_cell_paths:
            embryo_name, tp_this = os.path.basename(segmented_cell_file).split('_')[:2]
            saving_assigned_cell_path = os.path.join(segmented_root_path, embryo_name, selected_model,
                                                     output_saving_middle_path,
                                                     f'{embryo_name}_{tp_this}_segCell.nii.gz')

            annotated_niigz_path = os.path.join(segmented_root_path, embryo_name, selected_model, 'AnnoNuc',
                                                f'{embryo_name}_{tp_this}_annotatedNuc.nii.gz')
            parameters.append(
                [segmented_cell_file, cell_tree_embryo, annotated_niigz_path, embryo_name, cell2fate, label_name_dict,
                 saving_assigned_cell_path])

            # segment_membrane([embryo_name, file_name, embryo_mask])
        mp_cpu_num = min(len(parameters), max(mp.cpu_count() // 2, mp.cpu_count() - 10))
        mpPool = mp.Pool(mp_cpu_num)

        for _ in tqdm(mpPool.imap_unordered(running_reassign_cellular_map, parameters), total=len(parameters),
                      desc="{} membrane --> cell, all cpu process is {}, we created {}".format(
                          'assign cell label embryo',
                          str(mp.cpu_count()),
                          str(mp_cpu_num))):
            pass
        # =======================================================================================================

        # ========================================combine dividing cells=========================================
        segmented_cell_paths = sorted(glob(
            os.path.join(segmented_root_path, embryo_name, selected_model, output_saving_middle_path,
                         '*.nii.gz')))
        parameters_dividing = []
        for segmented_cell_file in segmented_cell_paths:
            embryo_name, tp_this = os.path.basename(segmented_cell_file).split('_')[:2]
            pred_memb_path = os.path.join(segmented_root_path, embryo_name, selected_model, 'SegMemb',
                                          f'{embryo_name}_{tp_this}_segMemb.nii.gz')
            annotated_file_path = os.path.join(segmented_root_path, embryo_name, selected_model, 'AnnoNuc',
                                               f'{embryo_name}_{tp_this}_annotatedNuc.nii.gz')
            parameters_dividing.append(
                [segmented_cell_file, pred_memb_path, annotated_file_path, cell_tree_embryo, name_label_dict,
                 label_name_dict])

            # segment_membrane([embryo_name, file_name, embryo_mask])
        mp_cpu_num = min(len(parameters_dividing), mp.cpu_count() // 2)
        mpPool = mp.Pool(mp_cpu_num)
        for _ in tqdm(mpPool.imap_unordered(combine_division_mp, parameters_dividing), total=len(parameters_dividing),
                      desc="{} cell --> dividing cells, all cpu process is {}, we created {}".format(
                          'assign cell label embryo',
                          str(mp.cpu_count()),
                          str(mp_cpu_num))):
            pass
        # =======================================================================================================


