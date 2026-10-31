# OLD VERSION FROM AN INITIAL CONCEPT THAT HAS BEEN IMPROVED UPON - OUTDATED
import pymupdf

pdf = pymupdf.open("orar_clase.pdf")
page = pdf[0]
Coordconst = 612;
day_boundaries = [Coordconst - 500, Coordconst - 405, Coordconst - 310, Coordconst - 220, Coordconst - 125, Coordconst - 30]
period_boundaries = [89, 142, 196, 249, 302, 335, 408, 462, 515, 568, 622, 674, 726, 780]


def find_interval(coordinate, boundaries):
    for i in range(len(boundaries) - 1):
        if boundaries[i] <= coordinate < boundaries[i + 1]:
            return i + 1

    return None

def classify_word(word, day_boundaries, period_boundaries):
    x0, y0, x1, y1 = word[:4]

    x = (x0 + x1) / 2
    y = (y0 + y1) / 2

    day = find_interval(y, day_boundaries)
    period = find_interval(x, period_boundaries)

    return day, period

words = page.get_text("words", sort=True)

for word in words:
    if len(word[4]) > 2:
        day, period = classify_word(
            word,
            day_boundaries,
            period_boundaries
        )

        print(word[4], day, period)

