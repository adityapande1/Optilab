import os, sys
import shutil
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
    original_backtest_folder = os.path.join(optiverse_dir, 'backtest_results')
    this_dir_backtest_folder = os.path.join(this_dir, 'optiverse_backtest_results')
    os.makedirs(this_dir_backtest_folder, exist_ok=True)

    num_backtests_to_copy = 10  # The number of backtests to copy from original source

    # Get last N backtests
    all_backtest = sorted(
        [f for f in os.listdir(original_backtest_folder) if f.startswith('backtest__')]
    )[-num_backtests_to_copy:]

    # Copy folders and add to git
    for backtest in all_backtest:
        src = os.path.join(original_backtest_folder, backtest)
        dest = os.path.join(this_dir_backtest_folder, backtest)
        shutil.copytree(src, dest, dirs_exist_ok=True)  # overwrite if exists
        os.system(f"git add 'optiverse_backtest_results/{backtest}'")

    # Commit and push
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