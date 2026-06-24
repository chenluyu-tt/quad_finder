import random
from itertools import combinations

import streamlit as st
import plotly.graph_objects as go


# =========================
# Basic settings
# =========================

DECK_SIZE = 64
DIMENSION = 6
GRID_SIZE = 8


# =========================
# Card / binary helpers
# =========================

def to_binary(card):
    return format(card, "06b")


def card_to_position(card):
    """
    Put cards 0,...,63 into an 8 x 8 grid.
    """
    row = card // GRID_SIZE
    col = card % GRID_SIZE
    return row, col


# =========================
# Quad functions
# =========================

def list_quads(hand):
    """
    Return all quads inside the selected hand.

    A quad satisfies a ^ b ^ c ^ d == 0.
    Equivalently, for any three cards a,b,c,
    the fourth card is d = a ^ b ^ c.
    """
    hand_set = set(hand)
    quads = set()

    for a, b, c in combinations(hand, 3):
        d = a ^ b ^ c

        if d in hand_set:
            quad = tuple(sorted([a, b, c, d]))
            quads.add(quad)

    return sorted(quads)


def count_quads(hand):
    return len(list_quads(hand))


def toggle_card(card):
    """
    Add/remove a card from the current hand.
    """
    hand = set(st.session_state.hand)

    if card in hand:
        hand.remove(card)
    else:
        hand.add(card)

    st.session_state.hand = sorted(hand)


# =========================
# Plotting
# =========================

def draw_grid(hand, quads, show_quad_lines=True):
    fig = go.Figure()

    # Draw grid lines
    for i in range(GRID_SIZE + 1):
        fig.add_shape(
            type="line",
            x0=i - 0.5,
            y0=-0.5,
            x1=i - 0.5,
            y1=GRID_SIZE - 0.5,
            line=dict(color="lightgray", width=1),
        )
        fig.add_shape(
            type="line",
            x0=-0.5,
            y0=i - 0.5,
            x1=GRID_SIZE - 0.5,
            y1=i - 0.5,
            line=dict(color="lightgray", width=1),
        )

    # Add all card labels in light gray
    all_x = []
    all_y = []
    all_text = []

    for card in range(DECK_SIZE):
        row, col = card_to_position(card)
        all_x.append(col)
        all_y.append(GRID_SIZE - 1 - row)
        all_text.append(to_binary(card))

    fig.add_trace(
        go.Scatter(
            x=all_x,
            y=all_y,
            mode="text",
            text=all_text,
            textfont=dict(size=10, color="lightgray"),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # Draw selected cards
    selected_x = []
    selected_y = []
    selected_text = []

    for card in hand:
        row, col = card_to_position(card)
        selected_x.append(col)
        selected_y.append(GRID_SIZE - 1 - row)
        selected_text.append(to_binary(card))

    fig.add_trace(
        go.Scatter(
            x=selected_x,
            y=selected_y,
            mode="markers+text",
            text=selected_text,
            textposition="middle center",
            marker=dict(
                symbol="diamond",
                size=42,
                color="mediumseagreen",
                line=dict(color="darkgreen", width=2),
            ),
            textfont=dict(size=11, color="black"),
            name="Selected cards",
        )
    )

    # Draw quad connections
    colors = [
        "red", "blue", "orange", "purple", "brown",
        "deeppink", "darkcyan", "goldenrod", "black", "darkgreen"
    ]

    if show_quad_lines:
        for i, quad in enumerate(quads):
            color = colors[i % len(colors)]

            xs = []
            ys = []

            # Sort by grid position only for drawing a loop
            quad_sorted = sorted(quad, key=lambda card: card_to_position(card))

            for card in quad_sorted:
                row, col = card_to_position(card)
                xs.append(col)
                ys.append(GRID_SIZE - 1 - row)

            # close the loop
            xs.append(xs[0])
            ys.append(ys[0])

            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="lines",
                    line=dict(color=color, width=4),
                    name="Quad {}".format(i + 1),
                )
            )

    fig.update_layout(
        width=850,
        height=850,
        plot_bgcolor="white",
        xaxis=dict(
            range=[-0.5, GRID_SIZE - 0.5],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
        ),
        yaxis=dict(
            range=[-0.5, GRID_SIZE - 0.5],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            scaleanchor="x",
            scaleratio=1,
        ),
        margin=dict(l=20, r=20, t=50, b=20),
        title="Quad-64 Finder: Dimension 6",
    )

    return fig


# =========================
# Streamlit app
# =========================

st.set_page_config(page_title="Quad-64 Finder", layout="wide")

st.title("Quad-64 Finder")
st.write("Deck: 64 cards, dimension 6, modeled as binary vectors in F₂⁶.")

if "hand" not in st.session_state:
    st.session_state.hand = []


# Sidebar controls
st.sidebar.header("Controls")

random_k = st.sidebar.slider("Random deal size k", min_value=1, max_value=20, value=8)
show_quad_lines = st.sidebar.checkbox("Show quad lines", value=True)

if st.sidebar.button("Random Deal"):
    st.session_state.hand = sorted(random.sample(range(DECK_SIZE), random_k))

if st.sidebar.button("Clear"):
    st.session_state.hand = []


# =========================
# Manual Selection FIRST
# =========================

st.subheader("Manual Selection")

st.write("Click a binary card button to add/remove it from the current hand.")

for row in range(GRID_SIZE):
    cols = st.columns(GRID_SIZE)

    for col in range(GRID_SIZE):
        card = row * GRID_SIZE + col
        label = to_binary(card)

        is_selected = card in st.session_state.hand

        button_label = "✅ " + label if is_selected else label

        with cols[col]:
            st.button(
                button_label,
                key="card_button_{}".format(card),
                on_click=toggle_card,
                args=(card,),
                use_container_width=True,
            )


# =========================
# Current data AFTER clicking
# =========================

hand = st.session_state.hand
quads = list_quads(hand)


# =========================
# Main display
# =========================

st.markdown("---")

col1, col2 = st.columns([3, 1])

with col1:
    fig = draw_grid(hand, quads, show_quad_lines=show_quad_lines)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Statistics")
    st.write("Selected cards:", len(hand))
    st.write("Number of quads:", len(quads))

    st.subheader("Hand")
    if hand:
        for card in hand:
            st.write(to_binary(card))
    else:
        st.write("No cards selected.")

    st.subheader("Quads")
    if quads:
        for i, quad in enumerate(quads, start=1):
            binary_quad = [to_binary(card) for card in quad]
            st.write("Quad {}:".format(i))
            st.write(binary_quad)
    else:
        st.write("No quads found.")