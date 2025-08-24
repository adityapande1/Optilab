# Optilab
Optilab is the `streamlit` visualizer repo for `Optiverse`. It helps the user to visualize and analyse backtesting results as well as candlestick chart for different stocks, options, indices, and combination thereof.

## Basic app structure `app.py`
Terminal command : `streamlit run app.py`   
This will start the Streamlit server and open the app in your default web browser. From here user can navigate to different other apps like a webpage. For each webpage a different `<new>.py` should be created and code simiar to the followin should be added

### Protocol for creating a new webpage
1. Create any new file with the prefix `app_` like `app_trade.py`, `app_analysis.py`, etc.
2. In the new file (say) `app_new.py` , define the `run()` function that contains the logic for the new page.
3. Import the `run()` function from `app_new.py` into `app.py` using the following line: `from app_new import run as run_new` in `app.py`.
4. Add the new page's navigation logic to  `app.py`. (Details below)

    ```python
    from app_new import run as run_new

    state_names = ["State_1", "State_2", ... "New Application"]
    button_names = ["btn_state_1", "btn_state_2", ... , "btn_new"]
    page_functions = {
        "State_1": run_state_1, # Import this function from state_1.py
        "State_2": run_state_2, # Import this function from state_2.py
        .
        .
        .
        "New Application": run_new  # Import this function from app_new.py
    }

    # Everything else will be taken care of by the existing logic
    ```

## Copying Files and Folders from Optiverse directory
`Optiverse` is a private repo in Github. Streamlit (free) need. a public repo for others wo be able to view the hosted app. Thats why you need to copy the necessary files and folders from the `Optiverse` directory to your public repo `Optilab`.

`main_copy_from_optiverse.py` does this. It operates in two steps. This script ensures that all the required assets are available for the Streamlit app to function correctly.

1. It copies the necessary files and folders from the `Optiverse` directory to the `Optilab` directory.
2. It then uses `os.system()` to Git commit and push these changes to the public repo. Note that not everything is pushed. Only the files and folders copied from `Optiverse` are pushed sequentially. For more details see the code.

PLEASE ADHERE TO THIS CONVENTION