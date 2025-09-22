import streamlit as st


def display_page_title(title, about, about_fontsize=28):
    st.markdown('---')
    st.markdown(f'# {title}')
    st.markdown(
        f"""
                <p style="
                    color: #da1b78;
                    font-size: {about_fontsize}px;
                    font-weight: bold;
                    padding: 1px;
                    text-align: left;
                    font-family: 'Lucida Console', monospace;
                    letter-spacing: 2px;
                    word-spacing: 4px;
                    line-height: 0.5;
                ">
                    {about}
                </p>
                """,
        unsafe_allow_html=True,
    )
    st.markdown('---')


box_style_small = """
    <div style="
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    ">
        <h5 style="color: #333; margin-bottom: 8px;">{title}</h5>
        <p style="font-size: 18px; font-weight: bold; color: #da1a78; text-align: center;">
            {value}
        </p>
    </div>
"""


def display_backtest_details(backtest_analyzer):
    strategy_config = backtest_analyzer.get_strategy_config().as_dict()
    backtester_config = backtest_analyzer.get_backtester_config().as_dict()
    about_strategy = backtest_analyzer.get_about()
    st.markdown('## Configuration Details')
    # Two main columns: left (configs), right (about)
    with st.expander('⚙️ Expand to view Backtest configs and strategy details', expanded=False):
        left_col, right_col = st.columns([1, 3])
        with left_col:
            st.subheader('📊 Backtest Config')
            st.write(backtester_config)
            st.subheader('📊 Strategy Config')
            st.write(strategy_config)

        with right_col:
            st.subheader('📊 About Strategy')
            rows_left = len(backtester_config) + len(strategy_config) + 5
            st.text_area('', value=about_strategy, height=29 * rows_left, label_visibility='collapsed')

    st.divider()
