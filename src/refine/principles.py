"""
The 16 Guiding Principles for Video Refinement

These principles define the quality bar for professional-level
educational videos. Each scene should be evaluated against all 16 principles.
"""

from dataclasses import dataclass
from typing import List

from .models import IssueType


@dataclass
class Principle:
    """A guiding principle for video refinement."""

    id: int
    name: str
    issue_type: IssueType
    description: str
    good_example: str
    bad_example: str
    checklist_question: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "issue_type": self.issue_type.value,
            "description": self.description,
            "good_example": self.good_example,
            "bad_example": self.bad_example,
            "checklist_question": self.checklist_question,
        }


GUIDING_PRINCIPLES: List[Principle] = [
    Principle(
        id=1,
        name="Show, don't tell",
        issue_type=IssueType.SHOW_DONT_TELL,
        description=(
            "If narration says 'six-fold explosion', visuals should feel explosive, "
            "not just show '6x'. The visual should embody the concept, not label it."
        ),
        good_example="Bar graph that rapidly expands with exponential easing, creating a 'wow' moment",
        bad_example="Static text showing '6x improvement'",
        checklist_question="Does the visual FEEL like what the narration describes?",
    ),
    Principle(
        id=2,
        name="Animation reveals understanding",
        issue_type=IssueType.ANIMATION_REVEALS,
        description=(
            "Motion should mirror how the concept works, not just be decorative. "
            "Animation should help viewers understand relationships and processes."
        ),
        good_example="Thinking steps appearing sequentially to show the AI's reasoning process",
        bad_example="Random fade-in animations that don't relate to the content",
        checklist_question="Does the animation help explain HOW the concept works?",
    ),
    Principle(
        id=3,
        name="Progressive disclosure",
        issue_type=IssueType.PROGRESSIVE_DISCLOSURE,
        description=(
            "Build information in sync with narration, never dump everything at once. "
            "Elements should appear WHEN the narration mentions them, not before."
        ),
        good_example="Numbers appear as narrator says them: '13.4%' then '83.3%'",
        bad_example="All stats visible from the start, spoiling the reveal",
        checklist_question="Do elements appear exactly when the narration mentions them?",
    ),
    Principle(
        id=4,
        name="Text that complements, not repeats",
        issue_type=IssueType.TEXT_COMPLEMENTS,
        description=(
            "Text on screen should ADD information the narration doesn't cover. "
            "Never show text that echoes what's being said - that's redundant."
        ),
        good_example="Showing AI's thinking traces ('Understanding the problem...') while narrator discusses results",
        bad_example="Displaying '83.3% vs 13.4%' as a subtitle while narrator says the same",
        checklist_question="Does on-screen text ADD new information, not repeat narration?",
    ),
    Principle(
        id=5,
        name="Visual hierarchy",
        issue_type=IssueType.VISUAL_HIERARCHY,
        description=(
            "One focal point at a time. Guide the eye deliberately using size, "
            "color, and position. The most important element should be obvious."
        ),
        good_example="83.3% displayed larger and brighter than 13.4% to emphasize the improvement",
        bad_example="Both numbers the same size, competing for attention",
        checklist_question="Is there ONE clear focal point? Is the most important element obvious?",
    ),
    Principle(
        id=6,
        name="Breathing room",
        issue_type=IssueType.BREATHING_ROOM,
        description=(
            "Give viewers time to absorb. Don't cram the frame with too many elements. "
            "White space is your friend - it helps focus attention."
        ),
        good_example="Clean layout with generous margins, one concept per visual area",
        bad_example="Cramped panels with tiny text competing for space",
        checklist_question="Does the viewer have time to absorb? Is there enough white space?",
    ),
    Principle(
        id=7,
        name="Purposeful motion",
        issue_type=IssueType.PURPOSEFUL_MOTION,
        description=(
            "Every animation should communicate something. No gratuitous movement. "
            "If something moves, it should be because the movement conveys meaning."
        ),
        good_example="Bar growing to show improvement - the growth IS the message",
        bad_example="Random bouncing or pulsing that doesn't relate to content",
        checklist_question="Does every animation serve a purpose? Would removing it lose meaning?",
    ),
    Principle(
        id=8,
        name="Emotional resonance",
        issue_type=IssueType.EMOTIONAL_RESONANCE,
        description=(
            "Visuals should evoke curiosity, surprise, the 'aha' moment. "
            "The viewer should FEEL something when key reveals happen."
        ),
        good_example="Dramatic pause before revealing the big number, then a satisfying 'pop'",
        bad_example="Flat, matter-of-fact presentation with no emotional peaks",
        checklist_question="Does the visual create curiosity, surprise, or an 'aha' moment?",
    ),
    Principle(
        id=9,
        name="Professional polish",
        issue_type=IssueType.PROFESSIONAL_POLISH,
        description=(
            "Smooth easing, proper alignment, no overlaps, no glitches. "
            "The video should feel like a polished production, not a draft."
        ),
        good_example="Elements perfectly aligned, smooth spring animations, consistent spacing",
        bad_example="Misaligned text, jerky animations, overlapping elements",
        checklist_question="Is everything aligned? Are animations smooth? Any visual glitches?",
    ),
    Principle(
        id=10,
        name="Sync with narration",
        issue_type=IssueType.SYNC_WITH_NARRATION,
        description=(
            "Key visual beats should land with key spoken beats. "
            "The visual 'punch' should coincide with the audio 'punch'."
        ),
        good_example="The '6.2x' badge pops in exactly when narrator says 'six-fold explosion'",
        bad_example="Visual reveals happening seconds before or after the related narration",
        checklist_question="Do visual beats align with audio beats? Do 'punches' land together?",
    ),
    Principle(
        id=11,
        name="Screen space utilization",
        issue_type=IssueType.SCREEN_SPACE_UTILIZATION,
        description=(
            "Fill the frame purposefully. Video is not PowerPoint — content should be "
            "sized for visual impact and mobile legibility. Avoid tiny elements clustered "
            "in the center with excessive empty space. Key numbers and reveals should "
            "command the frame."
        ),
        good_example="Key statistic '83.3%' displayed at 120px font dominating the center; diagrams span 60%+ of frame width",
        bad_example="Small content clustered in center leaving 40%+ of frame empty; tiny 14px expressions hard to read on mobile",
        checklist_question="Is content sized for impact? Would text be readable on a phone screen?",
    ),
    Principle(
        id=12,
        name="3D depth and material design",
        issue_type=IssueType.MATERIAL_DEPTH,
        description=(
            "UI components should feel like physical 3D objects with depth. Use multi-layer "
            "shadows (5-7 layers), bezel borders (light top/left, dark bottom/right), and inner "
            "shadows to create depth. Dark glass should be uniformly dark without grey gradient "
            "overlays. NEVER use perspective transforms to tilt elements for fake depth."
        ),
        good_example="Window with 6-layer drop shadow, bezel border, inner bottom shadow, thin top edge highlight, uniformly dark background",
        bad_example="Flat rectangle with single shadow, grey gradient overlay at top making it look washed out, or tilted with perspective transform",
        checklist_question="Do components feel like 3D objects? Multi-layer shadows? Bezel borders? No grey hue on dark elements?",
    ),
    Principle(
        id=13,
        name="Follows visual specification",
        issue_type=IssueType.VISUAL_SPEC_MATCH,
        description=(
            "THIS IS THE MOST IMPORTANT PRINCIPLE. The visual MUST STRICTLY match the specification "
            "in script.json's visual_cue field. The visual_cue is the EXACT specification - not a suggestion. "
            "Every element listed MUST be present. Every animation described MUST be implemented. "
            "Every visual effect mentioned MUST be visible. If the spec says '3D tree with branching animation', "
            "there MUST be a 3D-looking tree with actual branching animation - not a flat diagram or static tree. "
            "If the spec says 'withering effect for backtracking', there MUST be a visible withering animation. "
            "Missing ANY element from the spec = FAIL. Wrong animation style = FAIL. "
            "The visual_cue is the source of truth - implement it EXACTLY as described."
        ),
        good_example="Spec says '3D tree with branching exploration, withering backtrack, blooming success' → scene has 3D tree with all three animation types clearly visible",
        bad_example="Spec describes rich 3D tree animation but scene shows flat 2D diagram with basic fade effects",
        checklist_question="Does the visual implement EVERY element in the visual_cue? Are ALL described animations present? Does it match the spec EXACTLY, not approximately?",
    ),
    Principle(
        id=14,
        name="Text contrast and readability",
        issue_type=IssueType.TEXT_CONTRAST,
        description=(
            "Text MUST be readable against its background. On dark glass panels (rgba(18,20,25,0.98)), "
            "text MUST be white (#ffffff) or light gray (rgba(255,255,255,0.85)). NEVER use black or "
            "dark text on dark backgrounds - it will be invisible. Minimum font sizes: body text 16-18px * scale, "
            "titles 22-28px * scale, annotations 14-16px * scale. Small text is unreadable on mobile devices."
        ),
        good_example="White text (#ffffff) on dark glass panel, title at 24px * scale, body at 18px * scale - clearly readable",
        bad_example="Black or dark gray text on dark panel (invisible), or 12px text that's too small to read on mobile",
        checklist_question="Is text WHITE on dark backgrounds? Are font sizes large enough to read on mobile?",
    ),
    Principle(
        id=15,
        name="Element containment",
        issue_type=IssueType.ELEMENT_CONTAINMENT,
        description=(
            "All visual elements MUST stay within their parent container boundaries. Labels, badges, "
            "annotations, and floating elements should never overflow or extend outside their panels. "
            "If a label needs to appear 'above' a bar chart, leave room INSIDE the panel for it. "
            "Never use negative positioning that causes elements to escape their containers. "
            "Clipped or cut-off elements look unprofessional and broken."
        ),
        good_example="'100×' label positioned inside the graph panel with adequate margin from top edge",
        bad_example="'100×' label with top: -80px that extends above the panel boundary and gets clipped",
        checklist_question="Do ALL elements stay within their container bounds? Are there any clipped or overflowing elements?",
    ),
    Principle(
        id=16,
        name="Header spacing",
        issue_type=IssueType.HEADER_SPACING,
        description=(
            "Content panels must have adequate spacing from the scene title and subtitle. "
            "Minimum clearance should be 120-160px (scaled) below the title area. Panels that "
            "overlap or crowd the header look cramped and unprofessional. Use contentTop = "
            "LAYOUT.title.y + 140 or similar to ensure consistent spacing. Also leave ~100px "
            "at the bottom for the Reference component."
        ),
        good_example="Content panel starts at LAYOUT.title.y + 140, leaving clear space below 'The RLHF Foundation' title",
        bad_example="Panel starts at LAYOUT.title.y + 80, overlapping with or crowding the subtitle text",
        checklist_question="Is there adequate spacing between the title/subtitle and the first content panel? No overlap?",
    ),
]


def get_principle_by_id(principle_id: int) -> Principle | None:
    """Get a principle by its ID."""
    for p in GUIDING_PRINCIPLES:
        if p.id == principle_id:
            return p
    return None


def get_principle_by_issue_type(issue_type: IssueType) -> Principle | None:
    """Get a principle by its associated issue type."""
    for p in GUIDING_PRINCIPLES:
        if p.issue_type == issue_type:
            return p
    return None


def format_principles_for_prompt() -> str:
    """Format all principles as a string suitable for LLM prompts."""
    lines = ["The 16 Guiding Principles for Video Quality:\n"]

    for p in GUIDING_PRINCIPLES:
        lines.append(f"{p.id}. **{p.name}**")
        lines.append(f"   {p.description}")
        lines.append(f"   - Good: {p.good_example}")
        lines.append(f"   - Bad: {p.bad_example}")
        lines.append(f"   - Check: {p.checklist_question}")
        lines.append("")

    return "\n".join(lines)


def format_checklist_for_prompt() -> str:
    """Format principles as a checklist for quick evaluation."""
    lines = ["Visual Quality Checklist:\n"]

    for p in GUIDING_PRINCIPLES:
        lines.append(f"[ ] {p.id}. {p.name}: {p.checklist_question}")

    return "\n".join(lines)
