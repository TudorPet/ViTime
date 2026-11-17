import sys
from collections import defaultdict

import pymupdf

# Reuse the grid code from the previous file (like #include in C++).
from orar_merged_cells import TOL, get_vertical_lines, build_cells, detect_grid

BIG_FONT = 10          # text with a font size >= this is the subject
GROUP_PREFIX = "Group"  # label printed at the top of each group, e.g. "Group 1"
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri"]
TITLE_FONT = 30         # the class name ("10 A") is printed at about 33 pt

SUMMER, WINTER = "summer", "winter"
FIRST_PERIOD_START = 7 * 60 + 30     # 07:30, in minutes since midnight



# Period schedule: when each period starts and ends, for summer or winter hours.
#   summer: 50 min periods, 10 min break after every period
#   winter: 45 min periods, 5 min break, except 10 min after periods 3, 6, 9
#           (09:55-10:05, 12:30-12:40, 15:05-15:15)

WINTER_LONG_BREAK_AFTER = {3, 6, 9}   # periods followed by a 10 minute break


def period_times(season, n_periods=13):
    """Returns {period_number: "HH:MM - HH:MM"}, periods numbered from 1."""
    def fmt(minutes):
        return f"{minutes // 60:02d}:{minutes % 60:02d}"

    length = 45 if season == WINTER else 50
    times = {}
    start = FIRST_PERIOD_START
    for period in range(1, n_periods + 1):
        times[period] = f"{fmt(start)} - {fmt(start + length)}"
        if season == WINTER:
            pause = 10 if period in WINTER_LONG_BREAK_AFTER else 5
        else:
            pause = 10
        start += length + pause
    return times



# Step 1: horizontal lines (the thin lines that split a cell between groups)

def get_horizontal_lines(page):
    """Return every horizontal line on the page as (y, x_left, x_right)."""
    lines = []
    for path in page.get_drawings():
        for item in path["items"]:
            if item[0] == "l":
                p1, p2 = item[1], item[2]
                if abs(p1.y - p2.y) < 0.5:
                    lines.append((p1.y, min(p1.x, p2.x), max(p1.x, p2.x)))
    return lines



# Step 2: text "chunks" = runs of characters that were printed one after
# another. A room ("Sport1") and a teacher ("JoDo") are separate chunks even
# when they touch, because the second one starts with a jump backwards.

def get_text_chunks(page):
    chunks = []
    for block in page.get_text("rawdict")["blocks"]:
        if block["type"] != 0:                   # 0 = text, 1 = image
            continue
        current = None
        for line in block["lines"]:
            for span in line["spans"]:
                for ch in span["chars"]:
                    x0, y0, x1, y1 = ch["bbox"]
                    continues = (current is not None
                                 and abs(x0 - current["x1"]) < 1.0
                                 and abs(y0 - current["y0"]) < 1.0
                                 and abs(span["size"] - current["size"]) < 0.5)
                    if continues:
                        current["text"] += ch["c"]
                        current["x1"] = x1
                    else:
                        current = {"text": ch["c"], "size": span["size"],
                                   "x0": x0, "y0": y0, "x1": x1, "y1": y1}
                        chunks.append(current)
    return chunks



# Step 2b: the class's default room. aSc prints it once, right-aligned above
# the table (e.g. "Lb-s-Co"), and leaves it out of every cell that uses it.

def get_default_room(chunks, table_top, right_edge):
    for c in chunks:
        above_table = (c["y0"] + c["y1"]) / 2 < table_top
        right_aligned = abs(c["x1"] - right_edge) < 3
        if above_table and right_aligned:
            return c["text"].strip()
    return None                                  # this timetable has none



# Step 2c: the class name, printed large at the top centre of every page.

def get_class_name(chunks, table_top):
    title = [c for c in chunks
             if c["size"] >= TITLE_FONT and (c["y0"] + c["y1"]) / 2 < table_top]
    title.sort(key=lambda c: c["x0"])            # left to right: "10", "A"
    name = "".join("".join(c["text"].split()) for c in title)   # drop spaces
    return name or None



# Step 3: turn the chunks of ONE lesson (one group inside a cell) into a dict.

def read_lesson(chunks, left, right):
    subject_parts = []
    teacher = room = group = None

    for c in sorted(chunks, key=lambda c: (c["y0"], c["x0"])):
        text = c["text"].strip()
        if not text:
            continue
        if c["size"] >= BIG_FONT:
            subject_parts.append(text)           # long names wrap onto 2 lines
        elif text.startswith(GROUP_PREFIX):
            group = text
        else:
            gap_left = c["x0"] - left            # distance to the cell's left edge
            gap_right = right - c["x1"]          # ... and to its right edge
            if gap_right < gap_left:             # hugs the right edge -> teacher
                teacher = text
            else:                                # hugs the left edge  -> room
                room = text

    if not subject_parts and teacher is None and room is None:
        return None                              # empty
    return {"subject": "".join(subject_parts), "teacher": teacher,
            "room": room, "group": group}



# Step 4: walk over every cell of the timetable and collect its lessons.

def parse_lessons(page):
    grid = detect_grid(page)
    if grid is None:                             # not a timetable page
        return []
    table_top, day_boundaries, period_boundaries = grid
    cells = build_cells(get_vertical_lines(page), day_boundaries, period_boundaries)
    horizontals = get_horizontal_lines(page)
    chunks = get_text_chunks(page)
    default_room = get_default_room(chunks, table_top, period_boundaries[-1])
    class_name = get_class_name(chunks, table_top)

    lessons = []
    for day, day_cells in cells.items():
        top, bottom = day_boundaries[day - 1], day_boundaries[day]

        for first, last in day_cells:
            left, right = period_boundaries[first - 1], period_boundaries[last]

            # thin lines strictly inside this row that cross the whole cell
            splits = sorted({round(y, 1) for y, xa, xb in horizontals
                             if top + TOL < y < bottom - TOL
                             and xa <= left + TOL and xb >= right - TOL})
            bands = [top] + splits + [bottom]    # one band per group

            inside = [c for c in chunks
                      if left <= (c["x0"] + c["x1"]) / 2 < right
                      and top <= (c["y0"] + c["y1"]) / 2 < bottom]

            for b in range(len(bands) - 1):
                in_band = [c for c in inside
                           if bands[b] <= (c["y0"] + c["y1"]) / 2 < bands[b + 1]]
                lesson = read_lesson(in_band, left, right)
                if lesson is not None:
                    if lesson["room"] is None:       # no room in the cell ->
                        lesson["room"] = default_room  # the class's own room
                    lesson["class"] = class_name
                    lesson["day"] = day
                    lesson["periods"] = list(range(first, last + 1))
                    lessons.append(lesson)
    return lessons



# Step 5: flip the data around: class timetable -> per-teacher timetable.

def add_to_teacher_schedules(schedules, lessons):
    for lesson in lessons:
        if lesson["teacher"] is None:
            continue
        for period in lesson["periods"]:
            schedules[lesson["teacher"]].append({
                "day": lesson["day"], "period": period, "class": lesson["class"],
                "subject": lesson["subject"], "room": lesson["room"],
                "group": lesson["group"]})


if __name__ == "__main__":
    # usage:  python orar_teachers.py big_timetable.pdf
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "orar_toate_clasele.pdf"
    schedules = defaultdict(list)                # teacher -> list of entries

    for page in pymupdf.open(pdf_path):          # one page = one class
        lessons = parse_lessons(page)
        if not lessons:
            print(f"warning: no lessons found on page {page.number + 1}")
        add_to_teacher_schedules(schedules, lessons)

    for teacher in sorted(schedules):
        print(teacher)
        for e in sorted(schedules[teacher], key=lambda e: (e["day"], e["period"])):
            print(f"   {DAY_NAMES[e['day'] - 1]} period {e['period']:>2}  "
                  f"{e['class']:<4} {e['subject']:<8} room={e['room']} {e['group'] or ''}")
