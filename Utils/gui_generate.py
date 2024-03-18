import os
import glob
import numpy as np
# import nibabel as nib
from tqdm import tqdm
import pandas as pd
from csv import reader, writer

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from Utils.gui_data_io import check_folder, move_file,nib_save,nib_load
from Utils.gui_lineage_tree import construct_celltree,read_cd_file

def CMapAddZeroToUnresonableBlank(gui_source_data_path, gui_target_data_path, embryo_names):
    # max_times = {"200117plc1pop1ip3":155}
    for embryo_name in embryo_names:
        contact_file = pd.read_csv(os.path.join(gui_source_data_path, embryo_name, embryo_name + '_Stat.csv'), header=0,
                                   index_col=[0, 1])
        # for column_num,column_value in enumerate(contact_file.columns):
        #     print(column_num,column_value)
        # print(not contact_file.at[('Dap','Daaa'),str(144)]>=0)
        # print(not contact_file.loc[('Dap','Daaa')][143]>=0)
        # # Earap
        # # Earpp
        # print(not contact_file.at[('Earap','Earpp'),str(144)]>=0)
        #
        # input()
        for tp_index in contact_file.index:
            # print(embryo_name,'  contact pairs  ',tp_index)
            start_column = 0
            stop_column = 0
            first_flag = False
            # notNullIndex=contact_file.loc[tp_index].notna()
            for column_num, column_value in enumerate(contact_file.columns):
                # print(notNullIndex.loc[idx])
                if contact_file.at[tp_index, column_value] >= 0 and not first_flag:
                    start_column = column_num
                    first_flag = True
                if contact_file.at[tp_index, column_value] >= 0:
                    stop_column = column_num

            # print(start_column,stop_column)
            for col in range(start_column, stop_column + 1):
                # if tp_index == ('Dap', 'Daaa'):
                #     # print(start_column, stop_column)
                #     print(col,not contact_file.loc[tp_index][col]>=0)
                # if contact_file.loc[tp_index][col]<0:
                #     print('gagagaga')
                if not contact_file.loc[tp_index][col] >= 0:
                    # print(tp_index,col)
                    contact_file.loc[tp_index][col] = 0
            # print(notNullIndex)
        contact_file.to_csv(os.path.join(gui_target_data_path, embryo_name, embryo_name + '_Stat.csv'))


def transpose_csv(source_file, target_file):
    with open(source_file) as f, open(target_file, 'w', newline='') as fw:
        writer(fw, delimiter=',').writerows(zip(*reader(f, delimiter=',')))


def generate_cell_wise_gui_data(raw_image_folder,segmented_cell_folder,stat_data_folder, save_gui_folder, embryo_name, name_dictionary_path,cd_file_path):

    check_folder(os.path.join(save_gui_folder, embryo_name))
    move_file(os.path.join(stat_data_folder, embryo_name + "_surface.csv"),
              os.path.join(save_gui_folder, embryo_name, embryo_name + "_surface.csv"))

    move_file(os.path.join(stat_data_folder, embryo_name + "_volume.csv"),
              os.path.join(save_gui_folder, embryo_name, embryo_name + "_volume.csv"))
    # contact (with transpose)
    transpose_csv(os.path.join(stat_data_folder, embryo_name + "_contact.csv"),
                  os.path.join(save_gui_folder, embryo_name, embryo_name + "_Stat.csv"))

    # =======================copying rawmemb segmented membrane files=====================================
    raw_files = glob.glob(os.path.join(raw_image_folder, "*.nii.gz"))
    seg_files = glob.glob(os.path.join(segmented_cell_folder, "*.nii.gz"))
    assert len(raw_files)==len(seg_files)
    max_time=len(seg_files)
    # ======================copying raw membrane files==================================
    check_folder(os.path.join(save_gui_folder, embryo_name, "RawMemb"))
    for raw_file in raw_files:
        save_file = os.path.join(save_gui_folder, embryo_name, "RawMemb", os.path.basename(raw_file))
        move_file(raw_file, save_file)

    # ===================copying segmented cell files===================
    check_folder(os.path.join(save_gui_folder, embryo_name, "SegCell"))
    for seg_file in seg_files:
        save_file = os.path.join(save_gui_folder, embryo_name, "SegCell", os.path.basename(seg_file))
        move_file(seg_file, save_file)

    CMapAddZeroToUnresonableBlank(save_gui_folder, save_gui_folder, [embryo_name])

    # ================generate other necessary files
    volume_file = os.path.join(stat_data_folder, embryo_name + "_volume.csv")
    contact_file = os.path.join(stat_data_folder, embryo_name + "_contact.csv")
    volume_pd = pd.read_csv(volume_file, header=0, index_col=0)
    volume_pd.index = list(range(1, len(volume_pd.index) + 1, 1))  # todo:what is this?useless?
    contact_pd = pd.read_csv(contact_file, header=[0, 1], index_col=0)

    # ------------------------cd file nucleus----------------------------------
    label_name_dict = pd.read_csv(name_dictionary_path, index_col=0).to_dict()['0']
    name_label_dict = {value: key for key, value in label_name_dict.items()}
    ace_pd = read_cd_file(cd_file_path)
    cell_tree = construct_celltree(cd_file_path, max_time,name_dictionary_path)

    # ----------------save cells at TPCell folder
    bar = tqdm(total=len(volume_pd))
    bar.set_description("saving tp cells")
    for tp, row in volume_pd.iterrows():
        row = row.dropna()
        cell_names = list(row.index)
        cell_label = [name_label_dict[x] for x in cell_names]  # transfer the cell name to cell label

        write_file = os.path.join(save_gui_folder, embryo_name, "TPCell",
                                  "{}_{}_cells.txt".format(embryo_name, str(tp).zfill(3)))
        write_string = ",".join([str(int(x)) for x in cell_label]) + "\n"  # save the cell label for this tp
        check_folder(write_file)

        with open(write_file, "w") as f:
            f.write(write_string)
        bar.update(1)

    # save ****_lifecycle.csv
    write_file = os.path.join(save_gui_folder, embryo_name, "{}_lifescycle.csv".format(embryo_name))
    check_folder(write_file)

    open(write_file, "w").close()
    bar = tqdm(total=len(volume_pd.columns))  # go through volume csv
    bar.set_description("saving life cycle")
    for cell_col in volume_pd:  # go through volume csv (cell name)
        valid_index = volume_pd[cell_col].notnull()
        tps = list(volume_pd[valid_index].index)  # get the existing time point of this cell
        label_tps = [name_label_dict[cell_col]] + tps  # combine the cell label and the existing time as a list

        write_string = ",".join([str(x) for x in label_tps]) + "\n"

        with open(write_file, "a") as f:
            f.write(write_string)

    bar.update(1)

    # save neighbors ---GuiNeighbor
    contact_pd = contact_pd.replace(0, np.nan)
    bar = tqdm(total=len(contact_pd))
    bar.set_description("saving neighbors")
    for tp, row in contact_pd.iterrows():
        row = row.dropna()
        neighbors = {}
        pairs = sorted(list(row.index))
        if len(pairs) == 0:
            continue
        for cell1, cell2 in pairs:
            cell1 = name_label_dict[cell1]
            cell2 = name_label_dict[cell2]
            if cell1 not in neighbors:
                neighbors[cell1] = [cell2]
            else:
                neighbors[cell1] += [cell2]

            if cell2 not in neighbors:
                neighbors[cell2] = [cell1]
            else:
                neighbors[cell2] += [cell1]

        write_file = os.path.join(save_gui_folder, embryo_name, "GuiNeighbor",
                                  "{}_{}_guiNeighbor.txt".format(embryo_name, str(tp).zfill(3)))
        check_folder(write_file)

        open(write_file, "w").close()
        with open(write_file, "a") as f:

            for k, v in neighbors.items():  # cell label and its neighborhood
                labels = [k] + list(set(v))
                write_string = ",".join([str(int(x)) for x in labels]) + "\n"
                f.write(write_string)

        bar.update(1)

    # write  DivisionCell and lost cells
    bar = tqdm(total=len(volume_pd))
    bar.set_description("saving dividing or loss cells")
    for tp, row in volume_pd.iterrows():
        row = row.dropna()
        cur_ace_pd = ace_pd[ace_pd["time"] == tp]
        nuc_cells = list(cur_ace_pd["cell"])  # cell in cd file this time point
        seg_cells = list(row.index)  # cell in volume.csv this time point
        dif_cells = list(set(nuc_cells) - set(seg_cells))  # only get the additional cells; lost cell?

        division_cells = []
        lost_cells = []

        # get average radius
        radii_mean = np.power(row, 1 / 3).mean()
        lost_radius = radii_mean * 1.3

        # if tp == 179:
        #     print("TEST")

        for dif_cell in dif_cells:
            parent_cell = cell_tree.parent(dif_cell).tag
            sister_cells = [x.tag for x in cell_tree.children(parent_cell)]
            sister_cells.remove(dif_cell)
            sister_cell = sister_cells[0]
            # assert parent_cell in seg_cells
            # division_cells.append(parent_cell)
            if parent_cell in seg_cells:
                division_cells.append(parent_cell)
            else:
                # all_lost_cells.append("{}_{}_{}".format(embryo_name, dif_cell, str(tp).zfill(3)))
                lost_cells.append(dif_cell)
        # each tp
        division_cells = list(set(division_cells))
        lost_cells = list(set(lost_cells))
        division_cells = [name_label_dict[x] for x in division_cells]
        lost_cells = [name_label_dict[x] for x in lost_cells]

        write_file = os.path.join(save_gui_folder, embryo_name, "LostCell",
                                  "{}_{}_lostCell.txt".format(embryo_name, str(tp).zfill(3)))
        write_string = ",".join([str(int(x)) for x in lost_cells]) + "\n"
        check_folder(write_file)

        with open(write_file, "w") as f:
            f.write(write_string)

        write_file = os.path.join(save_gui_folder, embryo_name, "DivisionCell",
                                  "{}_{}_division.txt".format(embryo_name, str(tp).zfill(3)))
        write_string = ",".join([str(int(x)) for x in division_cells]) + "\n"
        check_folder(write_file)

        with open(write_file, "w") as f:
            f.write(write_string)

        bar.update(1)

# =========================
# change to fate-wise labels
# =========================
def change_labels(seg, label2name_dict, cell2fate, fate2label):
    new_seg = np.zeros_like(seg)
    labels = list(np.unique(seg))[1:]
    for label in labels:
        cell_name = label2name_dict[label]
        if cell_name in cell2fate.keys():
            cell_fate=cell2fate[cell_name]
        else:
            cell_fate =  'Unspecified'
            print(cell_name,'cell name fate not exist, and set to unspecified')
        tissue_label = fate2label[cell_fate]
        new_seg[seg == label] = tissue_label

    return new_seg
def generate_fate_wise_from_cell_wise_gui_data(fate_file_path, name_dictionary_path, cell_wise_gui_data_folder, embryo_name, to_save_fate_wise_folder):
    label_name_dict = pd.read_csv(name_dictionary_path, index_col=0).to_dict()['0']
    name_label_dict = {value: key for key, value in label_name_dict.items()}
    # =========================================================================
    # read cell fate, we have generate all cell fate under 550-cell stage
    # =========================================================================
    cell_fate = pd.read_excel(fate_file_path, names=["Cell", "Fate"], converters={"Cell": str, "Fate": str}, header=None)
    cell_fate = cell_fate.applymap(lambda x: x[:-1])
    cell2fate = dict(zip(cell_fate.Cell, cell_fate.Fate))
    all_fates = sorted(list(set(sorted(list(cell_fate.Fate)))))
    fate2label = dict(zip(all_fates, list(range(1, len(all_fates) + 1, 1))))

    # cell_fate_label_pairted_path = r'./dataset/CMapPairedFate.csv'
    # cell_fate["Cell label"] = cell_fate.apply(lambda x: name_label_dict.get(x["Cell"], None), axis=1)
    # cell_fate["Fate label"] = cell_fate.apply(lambda x: fate2label.get(x["Fate"], None), axis=1)
    # cell_fate.to_csv(cell_fate_label_pairted_path, index=False)

    raw_folder = os.path.join(cell_wise_gui_data_folder, embryo_name, "RawMemb")
    raw_files = sorted(glob.glob(os.path.join(raw_folder, "*.nii.gz")))
    seg_folder = os.path.join(cell_wise_gui_data_folder, embryo_name, "SegCell")
    seg_files = sorted(glob.glob(os.path.join(seg_folder, "*.nii.gz")))
    # max_time=len(seg_folder)


    save_file = os.path.join(to_save_fate_wise_folder, embryo_name, "SegCell", os.path.basename(seg_files[0]))
    check_folder(save_file)
    save_file = os.path.join(to_save_fate_wise_folder, embryo_name, "RawMemb", os.path.basename(raw_files[0]))
    check_folder(save_file)

    # ----------copy surface file (empty files)-----------------
    file_name = os.path.join(cell_wise_gui_data_folder, embryo_name, embryo_name + "_surface.csv")
    pd_data = pd.read_csv(file_name, index_col=0, header=0)
    pd_data = pd_data.applymap(lambda x: "")
    file_name = os.path.join(to_save_fate_wise_folder, embryo_name, embryo_name + "_surface.csv")
    check_folder(file_name)
    pd_data.to_csv(file_name)

    # --------copy volume file (empty files)----------------
    file_name = os.path.join(cell_wise_gui_data_folder, embryo_name, embryo_name + "_volume.csv")
    pd_data = pd.read_csv(file_name, index_col=0, header=0)
    pd_data = pd_data.applymap(lambda x: "")
    file_name = os.path.join(to_save_fate_wise_folder, embryo_name, embryo_name + "_volume.csv")
    pd_data.to_csv(file_name)

    # ---------copy contact are file (empty files)----------
    file_name = os.path.join(to_save_fate_wise_folder, embryo_name, embryo_name + "_Stat.csv")
    move_file(os.path.join(cell_wise_gui_data_folder, embryo_name, embryo_name + "_Stat.csv"), file_name)
    pd_data = pd.read_csv(file_name, index_col=None, header=0)
    pd_data = pd_data.applymap(lambda x: "")
    pd_data.to_csv(file_name, index=False)

    for raw_file, seg_file in zip(raw_files, seg_files):
        save_file = os.path.join(to_save_fate_wise_folder, embryo_name, "SegCell", os.path.basename(seg_file))
        # =======================change cell label flag to cell fate and save===================================
        seg = nib_load(seg_file)
        seg = change_labels(seg, label_name_dict, cell2fate, fate2label)
        nib_save(seg, save_file)
        # ======================save raw membrane======================
        save_file = os.path.join(to_save_fate_wise_folder, embryo_name, "RawMemb", os.path.basename(raw_file))
        move_file(raw_file, save_file)

    volume_file = os.path.join(cell_wise_gui_data_folder, embryo_name, "{}_volume.csv".format(embryo_name))
    # ace_file = os.path.join(embryo_data_source, 'CDFiles', "CD{}.csv".format(embryo_name))

    volume_pd = pd.read_csv(volume_file, header=0, index_col=0)
    volume_pd.index = list(range(1, len(volume_pd.index) + 1, 1))
    # celltree = construct_celltree(ace_file,max_time,name_dictionary_path)

    # save cells at tp
    # =================== save cell life span ======================================
    bar = tqdm(total=len(seg_files))
    bar.set_description("saving tp cells")
    for tp in range(1, len(seg_files) + 1, 1):
        write_file = os.path.join(to_save_fate_wise_folder, embryo_name, "TPCell",
                                  "{}_{}_cells.txt".format(embryo_name, str(tp).zfill(3)))
        cell_label = list(fate2label.values())
        write_string = ",".join([str(x) for x in cell_label]) + "\n"
        check_folder(write_file)

        with open(write_file, "w") as f:
            f.write(write_string)
        bar.update(1)

    # save lifecycle.csv
    write_file = os.path.join(to_save_fate_wise_folder, embryo_name, "{}_lifescycle.csv".format(embryo_name))
    check_folder(write_file)

    open(write_file, "w").close()
    bar = tqdm(total=len(volume_pd.columns))
    bar.set_description("saving life cycle")
    for cell_col in list(fate2label.values()):
        label_tps = [str(cell_col)] + list(range(1, len(volume_pd.index) + 1, 1))

        write_string = ",".join([str(x) for x in label_tps]) + "\n"

        with open(write_file, "a") as f:
            f.write(write_string)

    bar.update(1)

    # save neighbors
    bar = tqdm(total=len(seg_files))
    bar.set_description("saving neighbors")
    for tp in range(1, len(seg_files) + 1, 1):

        write_file = os.path.join(to_save_fate_wise_folder, embryo_name, "GuiNeighbor",
                                  "{}_{}_guiNeighbor.txt".format(embryo_name, str(tp).zfill(3)))
        check_folder(write_file)

        neighbors = {1: [2], 2: [1]}
        with open(write_file, "a") as f:

            for k, v in neighbors.items():
                labels = [k] + list(set(v))
                write_string = ",".join([str(x) for x in labels]) + "\n"
                f.write(write_string)

        bar.update(1)

    # write division and loss cell folder
    bar = tqdm(total=len(volume_pd))
    bar.set_description("saving divisions")
    for tp, row in volume_pd.iterrows():
        write_file = os.path.join(to_save_fate_wise_folder, embryo_name, "LostCell",
                                  "{}_{}_lostCell.txt".format(embryo_name, str(tp).zfill(3)))
        write_string = "\n"
        check_folder(write_file)

        with open(write_file, "w") as f:
            f.write(write_string)

        write_file = os.path.join(to_save_fate_wise_folder, embryo_name, "DivisionCell",
                                  "{}_{}_division.txt".format(embryo_name, str(tp).zfill(3)))
        write_string = "\n"
        check_folder(write_file)

        with open(write_file, "w") as f:
            f.write(write_string)

        bar.update(1)