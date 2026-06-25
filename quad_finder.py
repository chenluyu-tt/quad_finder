import random
import math
from itertools import combinations
from collections import Counter

import streamlit as st
import plotly.graph_objects as go
from PIL import Image, ImageDraw, ImageFont


# =========================
# Basic settings
# =========================

DECK_SIZE = 64
DIMENSION = 6
GRID_SIZE = 8

CARD_WIDTH = 140
CARD_HEIGHT = 200


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
# Card image generation
# =========================

def decode_card(card):
    """
    Decode a Quad-64 card into 3 attributes:
    - symbol: first 2 bits
    - color: middle 2 bits
    - number: last 2 bits
    """
    bits = to_binary(card)

    symbol_bits = bits[0:2]
    color_bits = bits[2:4]
    number_bits = bits[4:6]

    symbol_map = {
        "00": "spiral",
        "01": "diamond",
        "10": "circle",
        "11": "square",
    }

    color_name_map = {
        "00": "green",
        "01": "blue",
        "10": "pink",
        "11": "yellow",
    }

    color_rgb_map = {
        "00": (46, 160, 67),     # green
        "01": (52, 120, 246),    # blue
        "10": (220, 80, 150),    # pink
        "11": (230, 185, 40),    # yellow
    }

    number_map = {
        "00": 1,
        "01": 2,
        "10": 3,
        "11": 4,
    }

    return {
        "bits": bits,
        "symbol": symbol_map[symbol_bits],
        "color_name": color_name_map[color_bits],
        "color_rgb": color_rgb_map[color_bits],
        "number": number_map[number_bits],
    }


def draw_spiral(draw, cx, cy, size, color, width=4):
    """
    Draw a simple spiral approximation.
    """
    points = []
    turns = 2.5
    steps = 80

    for i in range(steps):
        t = i / (steps - 1)
        angle = turns * 2 * math.pi * t
        r = size * t
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        points.append((x, y))

    draw.line(points, fill=color, width=width)


def draw_diamond(draw, cx, cy, size, color, width=4):
    pts = [
        (cx, cy - size),
        (cx + size, cy),
        (cx, cy + size),
        (cx - size, cy),
        (cx, cy - size),
    ]
    draw.line(pts, fill=color, width=width)


def draw_circle(draw, cx, cy, size, color, width=4):
    draw.ellipse(
        (cx - size, cy - size, cx + size, cy + size),
        outline=color,
        width=width,
    )


def draw_square(draw, cx, cy, size, color, width=4):
    draw.rectangle(
        (cx - size, cy - size, cx + size, cy + size),
        outline=color,
        width=width,
    )


@st.cache_data
def render_card_image(card, selected=False):
    """
    Generate a card image for a given Quad-64 card.
    """
    info = decode_card(card)
    symbol = info["symbol"]
    color = info["color_rgb"]
    number = info["number"]
    bits = info["bits"]

    if selected:
        border_color = (0, 140, 70)
        bg = (235, 255, 242)
    else:
        border_color = (30, 30, 30)
        bg = "white"

    img = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), bg)
    draw = ImageDraw.Draw(img)

    # outer border
    draw.rounded_rectangle(
        (4, 4, CARD_WIDTH - 4, CARD_HEIGHT - 4),
        radius=12,
        outline=border_color,
        width=4,
    )

    # font
    try:
        font = ImageFont.truetype("arial.ttf", 16)
        small_font = ImageFont.truetype("arial.ttf", 14)
    except OSError:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # top binary label
    draw.text((12, 10), bits, fill=(50, 50, 50), font=font)

    # symbol positions
    y_positions_map = {
        1: [100],
        2: [75, 125],
        3: [60, 100, 140],
        4: [50, 85, 120, 155],
    }

    y_positions = y_positions_map[number]
    cx = CARD_WIDTH // 2
    size = 18

    for cy in y_positions:
        if symbol == "spiral":
            draw_spiral(draw, cx, cy, size, color, width=4)
        elif symbol == "diamond":
            draw_diamond(draw, cx, cy, size, color, width=4)
        elif symbol == "circle":
            draw_circle(draw, cx, cy, size, color, width=4)
        elif symbol == "square":
            draw_square(draw, cx, cy, size, color, width=4)

    # bottom card number label
    draw.text(
        (12, CARD_HEIGHT - 24),
        "card " + str(card),
        fill=(90, 90, 90),
        font=small_font,
    )

    return img


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
# Quad descriptions
# =========================

def classify_attribute(values):
    """
    For one attribute across 4 cards, classify the pattern.
    """
    counts = Counter(values)

    if len(counts) == 1:
        return "all same"

    if len(counts) == 4:
        return "all different"

    if len(counts) == 2 and sorted(counts.values()) == [2, 2]:
        return "Half"

    return "not a quad pattern"


def quad_attribute_description(quad):
    """
    Describe the quad using card attributes.
    """
    infos = [decode_card(card) for card in quad]

    symbols = [info["symbol"] for info in infos]
    colors = [info["color_name"] for info in infos]
    numbers = [info["number"] for info in infos]

    return {
        "symbol": classify_attribute(symbols),
        "color": classify_attribute(colors),
        "number": classify_attribute(numbers),
    }


def quad_geometric_description(quad):
    """
    Describe a quad as an affine 2-flat in F_2^6.

    If quad = {p, p+u, p+v, p+u+v},
    then p is a base point and u, v are two directions.
    """
    q = list(quad)
    p = q[0]

    others = q[1:]

    u = others[0] ^ p
    v = None

    for candidate in others[1:]:
        direction = candidate ^ p
        if direction != u:
            v = direction
            break

    if v is None:
        return "Could not compute directions."

    fourth = p ^ u ^ v

    return (
        "Affine 2-flat: "
        f"p = {to_binary(p)}, "
        f"u = {to_binary(u)}, "
        f"v = {to_binary(v)}. "
        f"The four cards are p, p+u, p+v, p+u+v."
    )


# =========================
# Drawing helper
# =========================

def order_quad_for_drawing(quad):
    """
    Order the four points around their center so that the polygon
    is drawn without crossing itself.
    """
    points = []

    for card in quad:
        row, col = card_to_position(card)
        x = col
        y = GRID_SIZE - 1 - row
        points.append((card, x, y))

    cx = sum(x for _, x, _ in points) / 4
    cy = sum(y for _, _, y in points) / 4

    points.sort(key=lambda p: math.atan2(p[2] - cy, p[1] - cx))

    return [card for card, _, _ in points]


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

            quad_ordered = order_quad_for_drawing(quad)

            for card in quad_ordered:
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


# =========================
# Sidebar controls
# =========================

st.sidebar.header("Controls")

random_k = st.sidebar.slider(
    "Random deal size k",
    min_value=1,
    max_value=20,
    value=8,
)

show_quad_lines = st.sidebar.checkbox(
    "Show quad lines",
    value=True,
)

if st.sidebar.button("Random Deal"):
    st.session_state.hand = sorted(random.sample(range(DECK_SIZE), random_k))

if st.sidebar.button("Clear"):
    st.session_state.hand = []


# =========================
# Current data
# =========================

hand = st.session_state.hand
quads = list_quads(hand)


# =========================
# Main display first
# =========================

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

            geo_desc = quad_geometric_description(quad)
            st.caption(geo_desc)

            attr_desc = quad_attribute_description(quad)
            st.caption(
                "Attributes: "
                f"symbol = {attr_desc['symbol']}, "
                f"color = {attr_desc['color']}, "
                f"number = {attr_desc['number']}"
            )
    else:
        st.write("No quads found.")



# =========================
# Generated card image grid
# =========================

st.markdown("---")
st.subheader("Generated Card Image Grid")

st.write("The same 64 cards are shown below as generated Quad card images.")

for row in range(GRID_SIZE):
    cols = st.columns(GRID_SIZE)

    for col in range(GRID_SIZE):
        card = row * GRID_SIZE + col
        is_selected = card in st.session_state.hand

        img = render_card_image(card, selected=is_selected)

        with cols[col]:
            st.image(img, use_container_width=True)

            if is_selected:
                st.button(
                    "Remove",
                    key="image_card_button_{}".format(card),
                    on_click=toggle_card,
                    args=(card,),
                    use_container_width=True,
                )
            else:
                st.button(
                    "Select",
                    key="image_card_button_{}".format(card),
                    on_click=toggle_card,
                    args=(card,),
                    use_container_width=True,
                )