import pymupdf

# Update:
# The grid (day rows / period columns) is no longer hard-coded: detect_grid()
# reads it from the lines drawn on each page, so a different page size or
# column width does not break anything.
TOL = 1.5  # points; how far a line may be from a boundary and still match it


def find_interval(coordinate, boundaries):
    for i in range(len(boundaries) - 1):
        if boundaries[i] <= coordinate < boundaries[i + 1]:
            return i + 1
    return None



# Step 1: read the vertical separator lines that are actually drawn.

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


def _cluster(values):
    """Merge values that are within TOL of each other (float noise) into one."""
    groups = []
    for v in sorted(values):
        if groups and v - groups[-1][-1] < TOL:
            groups[-1].append(v)
        else:
            groups.append([v])
    return [sum(g) / len(g) for g in groups]


def detect_grid(page):
    """
    Returns (table_top, day_boundaries, period_boundaries) for this page,
    or None if the page does not contain a timetable grid.

    - The ends of the tall vertical lines give the y positions: the first one
      is the top of the table, the rest are the day-row boundaries.
    - Period boundaries are the x positions of vertical lines that cover a whole
      day row (merged cells hide a line in some rows, so we take them from all
      rows together). The left-most one is the table's outer frame, left of the
      day-name column, so it is dropped.
    """
    verticals = [v for v in get_vertical_lines(page) if v[2] - v[1] > 40]
    if not verticals:
        return None
    ys = _cluster([y for _, y0, y1 in verticals for y in (y0, y1)])
    table_top, day_boundaries = ys[0], ys[1:]

    xs = set()
    for top, bottom in zip(day_boundaries, day_boundaries[1:]):
        for x, y0, y1 in verticals:
            if y0 <= top + TOL and y1 >= bottom - TOL:
                xs.add(x)
    period_boundaries = _cluster(xs)[1:]

    if len(day_boundaries) < 3 or len(period_boundaries) < 3:
        return None
    return table_top, day_boundaries, period_boundaries



# Step 2: for every day, work out which periods are fused into one cell.

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



# Step 3: classify a word -> (day, [every period its cell covers]).

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
    _, day_boundaries, period_boundaries = detect_grid(page)
    cells = build_cells(get_vertical_lines(page), day_boundaries, period_boundaries)

    slots = {}  # (day, period) -> list of words in that slot
    for word in page.get_text("words", sort=True):
        if len(word[4]) <= 2:
            continue
        day, periods = classify_word(word, day_boundaries, period_boundaries, cells)
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
