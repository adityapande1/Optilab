import plotly.graph_objects as go
import streamlit as st

def info_box(val, bg="#f9f9f9", color="#da1a78", border_color="black", font_size=28):
    if val:  # make sure val is not empty
        parts = val.split(" ", 1)
        first_word = parts[0]
        rest = parts[1] if len(parts) > 1 else ""
    else:
        first_word = ""
        rest = ""

    html_template = f"""
    <div style="
        display: block;
        text-align: left;
        padding: 8px 16px;
        border-radius: 8px;
        background-color: {bg};
        border: 2px solid {border_color};
        width: 100%;
        box-sizing: border-box;
        font-family: Arial, Helvetica, sans-serif;
        font-size: {font_size}px;
    ">
        <span style="color: black; font-weight: bold;">{first_word}</span>
        <span style="color: {color}; font-weight: bold;"> {rest}</span>
    </div>
    """
    st.markdown(html_template, unsafe_allow_html=True)


def stem_plot(df, colname="daily_pnl"):
    
    fig = go.Figure()

    # Separate positive and negative values
    pos_mask = df[colname] >= 0
    neg_mask = df[colname] < 0

    # Positive stems
    fig.add_trace(go.Scatter(
        x=df.index[pos_mask],
        y=df[colname][pos_mask],
        mode="markers",
        marker=dict(color="green", size=8),
        showlegend=False
    ))

    for x, y in zip(df.index[pos_mask], df[colname][pos_mask]):
        fig.add_trace(go.Scatter(
            x=[x, x],
            y=[0, y],
            mode="lines",
            line=dict(color="green", width=4),
            showlegend=False
        ))

    # Negative stems
    fig.add_trace(go.Scatter(
        x=df.index[neg_mask],
        y=df[colname][neg_mask],
        mode="markers",
        marker=dict(color="red", size=8),
        showlegend=False,
    ))

    for x, y in zip(df.index[neg_mask], df[colname][neg_mask]):
        fig.add_trace(go.Scatter(
            x=[x, x],
            y=[0, y],
            mode="lines",
            line=dict(color="red", width=4),
            showlegend=False
        ))

    # Layout
    fig.update_layout(
        title=f"{colname} Stem Plot",
        title_font_size=24,  # title font size
        font=dict(size=20),  # general font size
        height=600,
        xaxis_title="Date",
        yaxis_title=colname,
        showlegend=True,
        template="plotly_white",

        yaxis=dict(tickfont=dict(size=20),
                   showgrid=True, gridcolor='lightgray', gridwidth=1),  # y-axis tick font size
        xaxis=dict(tickfont=dict(size=16), nticks=30,
                   showgrid=True, gridcolor='lightgray', gridwidth=1),  # x-axis tick font size

        )

    return fig