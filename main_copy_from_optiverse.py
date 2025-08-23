import os, sys
def main():

    optiverse_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Optiverse'))
    this_dir = os.path.abspath(os.path.dirname(__file__))

    # 1. Folders that will be copied as is from optiverse with the 'optiverse_' prefix
    folders_to_copy = [
        os.path.join(optiverse_dir, 'connectors'),
        os.path.join(optiverse_dir, 'utils'),
    ]
    for folder in folders_to_copy:
        dest_folder = os.path.join(this_dir, 'optiverse_' + os.path.basename(folder))
        os.system(f"cp -r {folder} {dest_folder}")  # Copy and even rewrite if exists

    # Git commit and push changes
    os.system("git add .")
    os.system("git commit -m 'Update Optiverse copies'")
    os.system("git push")


if __name__ == "__main__":
    '''This is to be run periodically, so that the code changes in Optiverse are reflected in this directory.'''
    main()