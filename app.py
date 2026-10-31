import pymupdf

pdf = pymupdf.open("orar_clase_11A.pdf")
page = pdf[0]
Coordconst = 612;
day_boundaries = [Coordconst - 500, Coordconst - 405, Coordconst - 310, Coordconst - 220, Coordconst - 125, Coordconst - 30]
period_boundaries = [...]

words = page.get_text("words", sort=True)

words = [word for word in words if len(word[4]) > 2]

for word in words:
    x0, y0, x1, y1, text, *_ = word
    print(f"{text:15} X: {x0:7.1f} Y: {y0:7.1f}")

