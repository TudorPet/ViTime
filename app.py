import pymupdf
import streamlit as st
from collections import defaultdict
from orar_teachers import parse_lessons, add_to_teacher_schedules, DAY_NAMES

st.markdown("<h1 style='text-align: center;'>Teacher schedules</h1>", unsafe_allow_html=True) # center title

left, middle, right = st.columns([1, 2, 1])
with middle:
    st.image("logo.png", width="stretch")


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