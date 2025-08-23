import mplfinance as mpf
import matplotlib.pyplot as plt

def plot_vertical_candlecharts(df_list, title_list, figsize, center_ts, num_past_bars, num_future_bars, fontsize=20, minor_vlines=True, save_name=None):
    
    # Assert that all dataframes have the same index
    if not all(df.index.equals(df_list[0].index) for df in df_list):
        raise ValueError("All dataframes must have the same index.")

    # Add ema lines to each dataframe
    for df in df_list:
        df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()

    # Find the middle index, start index, and end index for slicing
    df_first = df_list[0]
    middle_ts = df_first[df_first.index >= center_ts].index[0]
    middle_index = df_first.index.get_loc(middle_ts)
    start_index = max(middle_index - num_past_bars, 0)
    end_index = min(middle_index + num_future_bars, len(df_first))

    # Save all the data frames to be plotted
    dfs2plot = [df.iloc[start_index:end_index].copy() for df in df_list]

    # Create subplots
    num_subplots = len(df_list)
    fig, axes = plt.subplots(num_subplots, 1, figsize=figsize, sharex=True)

    for id, df in enumerate(dfs2plot):
        apds = [
            mpf.make_addplot(df['EMA_21'], ax=axes[id], color='mediumvioletred', width=1),
            mpf.make_addplot(df['EMA_50'], ax=axes[id], color='black', width=1.5)
        ]

        # Plot the data
        mpf.plot(df, type='candle', ax=axes[id], addplot=apds, volume=False, style='binance')
        
        # Set the title_list[id] at an anchor box at upper left corner, rotated 90 degrees
        axes[id].text(0.025, .8, title_list[id], transform=axes[id].transAxes, fontsize=fontsize, verticalalignment='top', rotation=90)

        # Set ylimits for y-axis
        price_range = df['high'].max() - df['low'].min()
        axes[id].set_ylim(df['low'].min() - 0.1 * price_range, df['high'].max() + 0.1 * price_range)

        # Increase the font size of x-axis and y-axis labels
        axes[id].tick_params(axis='both', which='major', labelsize=fontsize)
        axes[id].tick_params(axis='both', which='minor', labelsize=fontsize)

        # Add grid lines
        axes[id].grid(True, linestyle='--', linewidth=1.5, alpha=0.95)

    # Add vertical lines at specific indices
    df_first = dfs2plot[0]
    int_indices915 = set(df_first.index.indexer_at_time("09:15:00").tolist())
    center_idx = df_first.index.get_loc(center_ts)
    int_indices_gap5 = set(list(range(0, len(df_first), 5))).difference(int_indices915).difference({center_idx})
    minor_indices = set(list(range(len(df_first)))).difference(int_indices915).difference(int_indices_gap5).difference({center_idx})

    for idx, ax in enumerate(axes):
        # Vline at all indices at 9:15 AM
        for index in int_indices915:
            ax.axvline(index, color='gold', linestyle='-', linewidth=10, alpha=0.25, zorder=-10)

        # Vline at center_ts
        ax.axvline(center_idx, color='aliceblue', linestyle='-', linewidth=7, alpha=1, zorder=-10)

        # Vline at all indices at 5 bar intervals
        for index in int_indices_gap5:
            ax.axvline(index, color='lightsteelblue', linestyle='-.', linewidth=3, alpha=0.5, zorder=-10)
        
        if minor_vlines:
            # Vline at all minor indices
            for index in minor_indices:
                ax.axvline(index, color='grey', linestyle='-.', linewidth=0.5, alpha=0.75, zorder=-10)

    # decrease space between subplots
    plt.subplots_adjust(hspace=0.00025)
    plt.tight_layout()


    if save_name.endswith('.pdf'):
        plt.savefig(save_name, bbox_inches='tight', dpi=600, format='pdf')
    elif save_name:
        plt.savefig(save_name, bbox_inches='tight', dpi=300)
    else:
        plt.show()