import os, sys
def main():

    optiverse_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Optiverse'))
    this_dir = os.path.abspath(os.path.dirname(__file__))

    ########################################################################################
    ### 1. Folders that will be copied as is from optiverse with the 'optiverse_' prefix ###
    ########################################################################################

    folders_to_copy_from_optiverse = [
        os.path.join(optiverse_dir, 'connectors'),
        os.path.join(optiverse_dir, 'utils'),
    ]
    folders_copied = []
    for folder in folders_to_copy_from_optiverse:
        dest_folder = os.path.join(this_dir, 'optiverse_' + os.path.basename(folder))
        os.system(f"cp -r {folder} {dest_folder}")  # Copy and even rewrite if exists
        folders_copied.append(dest_folder)

    # Git commit and push changes only the above folders that were copied from optiverse
    os.system("git add " + " ".join(folders_copied))
    os.system("git commit -m 'Updated Optiverse folders'")
    os.system("git push")

    ########################################################################################
    ########################################################################################

    ###########################################################################################
    ### 2. Copy the last 10 backtest_results from the backtest folder and commit###
    ###########################################################################################
    import ipdb; ipdb.set_trace()
    backtest_folder = os.path.join(optiverse_dir, 'backtest_results')
    this_dir_backtest_folder = os.path.join(this_dir, 'optiverse_backtest_results')
    os.makedirs(this_dir_backtest_folder, exist_ok=True)  # Create if not exists
    num_backtests_to_copy = 10
    all_backtest = sorted([foldername for foldername in os.listdir(backtest_folder) if 'backtest__' in foldername])
    all_backtest = all_backtest[-num_backtests_to_copy:]
    git_folders = []
    for backtest in all_backtest:
        src_folder = os.path.join(backtest_folder, backtest)
        dest_folder = os.path.join(this_dir_backtest_folder, backtest)
        os.system(f"cp -r {src_folder} {dest_folder}")
        git_folders.append( os.path.join('optiverse_backtest_results', backtest))

    import ipdb; ipdb.set_trace()
    # Git commit and push changes only the above folders that were copied from optiverse
    for folder in git_folders:
        os.system(f"git add '{folder}'")
    os.system("git commit -m 'Updated Optiverse backtest results'")
    os.system("git push")

    ###########################################################################################
    ###########################################################################################


    ###########################################################################################
    ### 2. Add Logic here to update the database according to the optiverse database folder ###
    ###########################################################################################

    # TODO: Implement database update logic here

    ###########################################################################################
    ###########################################################################################




if __name__ == "__main__":
    '''This is to be run periodically, so that the code changes in Optiverse are reflected in this directory.'''
    main()