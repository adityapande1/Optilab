# Optilab
Optilab is the `streamlit` visualizer repo for `Optiverse`. It helps the user to visualize and analyse backtesting results as well as candlestick chart for different stocks, options, indices, and combination thereof.

## Basic app structure `app.py`
Terminal command : `streamlit run app.py`   
This will start the Streamlit server and open the app in your default web browser. From here user can navigate to different other apps like a webpage. For each webpage a different `<new>.py` should be created and code simiar to the followin should be added

### Protocol for creating a new webpage
1. Create a new Python file named `new.py` in the project directory with a `run()` function encapsulating the page's logic.
3. Import the `run()` function from `new.py` into `app.py` using the following line: `from new import run as run_new` in `app.py`.
4. Add the new page's navigation logic to  `app.py`. (Details below)

    ```python
    # In app.py append these three things

    state_names = ["State_1", "State_2", ... "New"]
    button_names = ["btn_state_1", "btn_state_2", ... , "btn_new"]
    page_functions = {
        "State_1": run_state_1, # Import this function from state_1.py
        "State_2": run_state_2, # Import this function from state_2.py
        .
        .
        .
        "New": run_new  # Import this function from new.py
    }
    
    ```


