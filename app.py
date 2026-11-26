import pymupdf
import streamlit as st
from collections import defaultdict
from orar_teachers import parse_lessons, add_to_teacher_schedules, DAY_NAMES, period_times, find_free_rooms

    
st.markdown("<h1 style='text-align: center;'>ViTime</h1>", unsafe_allow_html=True) # center title

left, middle, right = st.columns([1, 2, 1]) # center logo - modify middle column number in order to enlarge
with middle:
    st.image("logo.png", width="stretch")

st.markdown(
    """
    <div style="position: fixed; bottom: 10px; right: 15px;
                font-size: 1rem; color: gray; z-index: 100;">
        made with <3 by T @ VianuEngineering
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("""
**How to use the app**
1. Upload the PDF with the timetables (one class per page).
2. Choose a teacher from the list.
3. The table shows every lesson that teacher has, by day and period.
4. Use the toggle to switch between summer and winter hours.
""")

winter = st.toggle("❄️ Winter hours")  # off = summer hours
times = period_times("winter" if winter else "summer")

uploaded = st.file_uploader("Upload the timetable PDF", type="pdf")

@st.cache_data(show_spinner="Reading the PDF...")
def load_lessons(pdf_bytes):
    # cached: the PDF is only read again when a different file is uploaded
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    lessons = []
    for page in doc:
        lessons.extend(parse_lessons(page))
    return lessons

if uploaded:
    lessons = load_lessons(uploaded.getvalue())

    if not lessons:
        st.warning("No lessons were found in this PDF.")
    else:
        schedules = defaultdict(list)
        add_to_teacher_schedules(schedules, lessons)

        tab_teacher, tab_rooms = st.tabs(["Teacher schedule", "Free rooms"])

        with tab_teacher:
            teacher = st.selectbox("Teacher", sorted(schedules))
            entries = sorted(schedules[teacher], key=lambda e: (e["day"], e["period"]))
            rows = [
            {
                "Day": DAY_NAMES[e["day"] - 1],
                "Period": e["period"],
                "Time": times.get(e["period"], ""),
                "Class": e["class"],
                "Subject": e["subject"],
                "Room": e["room"],
                "Group": e["group"] or "",
            }
            for e in entries
            ]
            st.table(rows)

        with tab_rooms:
            col_day, col_period = st.columns(2)
            day = col_day.selectbox("Day", range(1, 6),
                                    format_func=lambda d: DAY_NAMES[d - 1])
            period = col_period.selectbox("Period", list(times),
                                          format_func=lambda p: f"{p}  ({times[p]})")

            free, busy = find_free_rooms(lessons, day, period)

            st.subheader(f"Free rooms: {len(free)}")
            st.write(", ".join(free) if free else "No free rooms at this time.")

            with st.expander(f"Occupied rooms: {len(busy)}"):
                st.table([{"Room": room, "Used by": "; ".join(users)}
                          for room, users in busy.items()])

