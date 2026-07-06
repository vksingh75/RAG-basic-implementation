#!/usr/bin/env python3
"""Generate scripts/sample/sample.pdf — a small multi-section, multi-page PDF
used by scripts/e2e_smoke.sh.

Content is deliberately factual and quotable (distinctive names and numbers)
so retrieval + citation assertions have unambiguous targets. Requires
reportlab (falls back with a clear error if unavailable).

Usage: python3 scripts/sample/gen_sample.py
"""

import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample.pdf")

SECTIONS = [
    (
        "1. Overview of the Meridian Deep-Sea Observatory",
        [
            "The Meridian Deep-Sea Observatory is a fictional underwater research "
            "station located 2,450 meters below the surface of the Pacific Ocean, "
            "approximately 310 kilometers southwest of the Aleutian Trench. It was "
            "commissioned in March 2019 and is operated by a consortium of four "
            "research institutes.",
            "The observatory's primary mission is the long-term monitoring of "
            "hydrothermal vent ecosystems. Its titanium pressure hull can withstand "
            "pressures of up to 380 atmospheres, and the station accommodates a "
            "rotating crew of twelve researchers on ninety-day tours.",
        ],
    ),
    (
        "2. Power and Life Support Systems",
        [
            "Primary power is supplied by a 850-kilowatt solid-oxide fuel cell "
            "array, with a secondary bank of lithium-iron-phosphate batteries "
            "providing 72 hours of emergency reserve. Power distribution is managed "
            "by the HALCYON control system, which balances loads across seven "
            "independent circuits.",
            "Life support relies on an electrolytic oxygen generator producing "
            "24 kilograms of oxygen per day, paired with lithium hydroxide "
            "scrubbers that remove carbon dioxide. Potable water is reclaimed at a "
            "rate of 96 percent through a three-stage filtration cascade.",
            "In the event of a HALCYON fault, the station automatically enters "
            "low-power mode within 40 seconds, shutting down all non-essential "
            "laboratories while maintaining habitat pressure and communications.",
        ],
    ),
    (
        "3. Research Programs and Instrumentation",
        [
            "The observatory hosts three standing research programs: the Vent "
            "Fauna Census, the Geochemical Flux Survey, and the Acoustic Ecology "
            "Initiative. The Vent Fauna Census has catalogued 217 distinct species "
            "since operations began, including 31 previously undescribed species "
            "of amphipod.",
            "Instrumentation includes a pair of remotely operated vehicles named "
            "Kestrel and Cormorant, a 40-meter sensor mast with temperature and "
            "sulfide probes, and a broadband hydrophone array sampling at "
            "192 kilohertz. Data is relayed to shore through a fiber-optic cable "
            "with a sustained throughput of 10 gigabits per second.",
        ],
    ),
    (
        "4. Safety Protocols and Evacuation Procedures",
        [
            "All crew members complete a 21-day certification course before "
            "deployment, covering hyperbaric first aid, hull breach response, and "
            "submersible egress. Emergency drills are conducted every Tuesday at "
            "14:00 station time.",
            "Evacuation is performed using two six-person ascent capsules, each "
            "rated for a controlled ascent of 1.2 meters per second. A full "
            "station evacuation, from alarm to capsule release, is required to "
            "complete within eighteen minutes.",
            "The station maintains a 30-day emergency ration supply and a "
            "redundant acoustic beacon that transmits on 8.8 kilohertz should the "
            "fiber-optic link fail.",
        ],
    ),
]


def main() -> None:
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(
        OUT,
        pagesize=A4,
        title="Meridian Deep-Sea Observatory: Operations Handbook",
        author="RAG-basic-implementation sample",
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    story = [
        Paragraph("Meridian Deep-Sea Observatory: Operations Handbook", styles["Title"]),
        Paragraph(
            "A sample document for end-to-end retrieval and citation testing.",
            styles["Italic"],
        ),
        Spacer(1, 16),
    ]

    for i, (heading, paragraphs) in enumerate(SECTIONS):
        # Force a page break midway so the PDF spans multiple pages.
        if i == 2:
            story.append(PageBreak())
        story.append(Paragraph(heading, styles["Heading1"]))
        for text in paragraphs:
            story.append(Paragraph(text, styles["BodyText"]))
            story.append(Spacer(1, 8))
        story.append(Spacer(1, 12))

    doc.build(story)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
