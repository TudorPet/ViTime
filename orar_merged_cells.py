import pymupdf

# ---------------------------------------------------------------------------
# Grid geometry (read off the vector lines of the aSc PDF, in PDF points).
# Rows = Mon..Fri, columns = periods 1..13.
# ---------------------------------------------------------------------------

DAY_BOUNDARIES = [113.2, 206.8, 300.5, 394.1, 487.7, 581.4]
PERIOD_BOUNDARIES = [88.9, 142.1, 195.2, 248.4, 301.4, 354.6, 407.8,
                     460.9, 514.1, 567.1, 620.3, 673.4, 726.6, 779.8]

TOL = 1.5  # tolerance -> how far a line may be from a boundary and still match it


def find_interval(coordinate, boundaries):
    for i in range(len(boundaries) - 1):
        if boundaries[i] <= coordinate < boundaries[i + 1]:
            return i + 1
    return None


# Step 1: read the vertical separator lines that are actually drawn
def get_vertical_lines(page):
    """Return every vertical line on the page as (x, y_top, y_bottom)."""
    verticals = []
    for path in page.get_drawings():
        for item in path["items"]:
            if item[0] == "l":                      # a straight line segment
                p1, p2 = item[1], item[2]
                if abs(p1.x - p2.x) < 0.5:          # ...that is vertical
                    verticals.append((p1.x, min(p1.y, p2.y), max(p1.y, p2.y)))
    return verticals


# Step 2: for every day, work out which periods are fused into one cell

def build_cells(verticals, day_boundaries, period_boundaries):
    """
    Returns {day: [(first_period, last_period), ...]}.

    A cell is the stretch between two consecutive "closed" period boundaries.
    A boundary is closed in a given day row if a vertical line is drawn there
    over the whole height of that row. Where aSc merged cells, that line is
    simply missing, so the neighbouring periods end up in the same cell.
    """
    n = len(period_boundaries) - 1
    cells = {}
    for d in range(len(day_boundaries) - 1):
        top, bottom = day_boundaries[d], day_boundaries[d + 1]
        closed = {0, n}                              # outer edges always close
        for x, y0, y1 in verticals:
            if y0 <= top + TOL and y1 >= bottom - TOL:       # spans the row
                for i, bx in enumerate(period_boundaries):
                    if abs(x - bx) < TOL:
                        closed.add(i)
        edges = sorted(closed)
        # edge a .. edge b covers periods a+1 .. b (1-based)
        cells[d + 1] = [(a + 1, b) for a, b in zip(edges, edges[1:])]
    return cells


# Step 3: classify a word -> (day, [every period its cell covers])

def classify_word(word, day_boundaries, period_boundaries, cells):
    x0, y0, x1, y1 = word[:4]
    x = (x0 + x1) / 2
    y = (y0 + y1) / 2

    day = find_interval(y, day_boundaries)
    period = find_interval(x, period_boundaries)
    if day is None or period is None:
        return None, []

    for first, last in cells[day]:
        if first <= period <= last:
            return day, list(range(first, last + 1))
    return day, [period]


def parse_timetable(path):
    page = pymupdf.open(path)[0]
    cells = build_cells(get_vertical_lines(page), DAY_BOUNDARIES, PERIOD_BOUNDARIES)

    slots = {}  # (day, period) -> list of words in that slot
    for word in page.get_text("words", sort=True):
        if len(word[4]) <= 2 and word[4] != "CG":   # Edge case with CG
            continue
        day, periods = classify_word(word, DAY_BOUNDARIES, PERIOD_BOUNDARIES, cells)
        for period in periods:                       # "virtual unmerge"
            slots.setdefault((day, period), []).append(word[4])
    return cells, slots


if __name__ == "__main__":
    cells, slots = parse_timetable("orar_clase_10A.pdf")
    for day, day_cells in cells.items():
        merged = [c for c in day_cells if c[0] != c[1]]
        if merged:
            print("day", day, "merged cells (first, last period):", merged)
    for key in sorted(slots):
        print(key, slots[key])