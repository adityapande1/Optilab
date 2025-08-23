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
        os.path.join(optiverse_dir, 'strategy'),
        os.path.join(optiverse_dir, 'backtest'),
    ]
    folders_copied = []
    for folder in folders_to_copy_from_optiverse:
        dest_folder = os.path.join(this_dir, os.path.basename(folder))
        if os.path.exists(dest_folder):
            shutil.rmtree(dest_folder)  # Remove existing destination folder
        os.system(f"cp -r {folder} {dest_folder}")  # Copy and even rewrite if exists
        folders_copied.append(dest_folder)

    # Git commit and push changes only the above folders that were copied from optiverse
    os.system("git add " + " ".join(folders_copied))
    os.system("git commit -m 'Updated Optiverse folders'")
    os.system("git push")

    print("\n" + "#"*80)
    print("#"*5 + " Copied folders from Optiverse and pushed to git ".center(70) + "#"*5)
    print("#"*80 + "\n")
    ###########################################################################################
    ###########################################################################################

    ###########################################################################################
    ### 2. Copy the last <num_backtests_to_copy> backtest_results from Optiverse and commit ###
    ###########################################################################################
    original_backtest_folder = os.path.join(optiverse_dir, 'backtest_results')
    this_dir_backtest_folder = os.path.join(this_dir, 'backtest_results')
    os.makedirs(this_dir_backtest_folder, exist_ok=True)
    # Remove all contents in the backtest results folder
    for f in os.listdir(this_dir_backtest_folder):
        shutil.rmtree(os.path.join(this_dir_backtest_folder, f))

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
        os.system(f"git add 'backtest_results/{backtest}'")

    # Commit and push
    os.system("git commit -m 'Updated Optiverse backtest results'")
    os.system("git push")

    print("\n" + "#"*80)
    print("#"*5 + " Copied backtest results from Optiverse and pushed to git ".center(70) + "#"*5)
    print("#"*80 + "\n")
    ###########################################################################################
    ###########################################################################################

    ###########################################################################################
    ### 3. Copy paste exact database folder ###
    ###########################################################################################
    original_database_folder = os.path.join(optiverse_dir, 'database')
    this_dir_database_folder = os.path.join(this_dir, 'database')
    os.makedirs(this_dir_database_folder, exist_ok=True)

    # Remove all contents in the database folder
    for f in os.listdir(this_dir_database_folder):
        path = os.path.join(this_dir_database_folder, f)
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

    # Copy database files
    shutil.copytree(original_database_folder, this_dir_database_folder, dirs_exist_ok=True)
    print("\n" + "#"*80)
    print("#"*5 + " Copied database folder from Optiverse ".center(70) + "#"*5)
    print("#"*80 + "\n")
    ###########################################################################################
    ###########################################################################################

    ###########################################################################################
    ### 4. Copy paste .py files 
    ###########################################################################################
    original_py_file_path = os.path.join(optiverse_dir, 'Constants.py')
    this_dir_py_file_path = os.path.join(this_dir, 'Constants.py')
    shutil.copy2(original_py_file_path, this_dir_py_file_path)


    # Git commit and push changes only the above folders that were copied from optiverse
    os.system(f"git add {this_dir_py_file_path}")
    os.system("git commit -m 'Updated Constants.py'")
    os.system("git push")

    print("\n" + "#"*80)
    print("#"*5 + " Copied .py files from Optiverse ".center(70) + "#"*5)
    print("#"*80 + "\n")
    ###########################################################################################
    ###########################################################################################


if __name__ == "__main__":
    '''This is to be run periodically, so that the code changes in Optiverse are reflected in this directory.'''
    main()