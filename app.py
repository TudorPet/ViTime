import pymupdf
import streamlit as st
from collections import defaultdict
from orar_teachers import parse_lessons, add_to_teacher_schedules, DAY_NAMES

st.markdown("<h1 style='text-align: center;'>ViTime</h1>", unsafe_allow_html=True) # center title
st.markdown(
    """
    <div style="position: fixed; bottom: 10px; right: 15px;
                font-size: 1rem; color: gray; z-index: 100;">
        made with <3 by T
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("""
**How to use the app**
1. Upload the PDF with the timetables (one class per page).
2. Choose a teacher from the list.
3. The table shows every lesson that teacher has, by day and period.
""")


uploaded = st.file_uploader("Upload the timetable PDF", type="pdf")

if uploaded:
    doc = pymupdf.open(stream=uploaded.read(), filetype="pdf")
    schedules = defaultdict(list)
    for page in doc:
        add_to_teacher_schedules(schedules, parse_lessons(page))

    teacher = st.selectbox("Teacher", sorted(schedules))
    entries = sorted(schedules[teacher], key=lambda e: (e["day"], e["period"]))
    rows = [
    {
        "Day": DAY_NAMES[e["day"] - 1],
        "Period": e["period"],
        "Class": e["class"],
        "Subject": e["subject"],
        "Room": e["room"],
        "Group": e["group"] or "",
    }
    for e in entries
    ]
    st.table(rows)

left, middle, right = st.columns([1, 2, 1]) # center logo - modify middle column number in order to enlarge
with middle:
    st.image("logo.png", width="stretch")
