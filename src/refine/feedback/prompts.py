"""LLM prompts for feedback processing."""

PARSE_FEEDBACK_SYSTEM_PROMPT = """You are analyzing user feedback for a video explainer project.

Your task is to:
1. Determine what KIND of change is being requested (intent)
2. Identify which SCENES are affected
3. Provide a clear INTERPRETATION of what the user wants

Be precise and specific. The feedback will be used to generate patches that modify project files."""


PARSE_FEEDBACK_PROMPT = """Analyze this user feedback for a video project.

## Project: {project_id}

## Available Scenes:
{scene_list}

## User Feedback:
"{feedback_text}"

## Intent Categories
Choose the most specific intent:
- script_content: Changing what is SAID in the narration (voiceover text)
- script_structure: Adding, removing, or reordering SCENES
- visual_cue: Changing the DESCRIPTION of what should be visualized (in script.json)
- visual_impl: Changing the ACTUAL CODE that renders the scene (.tsx files)
- timing: Adjusting scene DURATIONS
- style: Changing visual STYLING patterns (colors, fonts, shadows, etc.)
- mixed: Multiple types of changes (specify sub_intents)

## Instructions
1. Read the feedback carefully
2. Identify the primary intent
3. List affected scene IDs (use the slug format like "the_impossible_leap")
4. Provide a clear interpretation

Respond with JSON:
{{
    "intent": "script_content|script_structure|visual_cue|visual_impl|timing|style|mixed",
    "sub_intents": ["intent1", "intent2"],  // Only if intent is "mixed"
    "affected_scene_ids": ["scene_id_1", "scene_id_2"],  // Empty list for project-wide
    "scope": "scene|multi_scene|project",
    "interpretation": "Clear, actionable description of what the user wants changed"
}}
"""


GENERATE_SCRIPT_PATCH_PROMPT = """Generate patches to modify the narration/script based on this feedback.

## Scene Information
Scene ID: {scene_id}
Scene Title: {scene_title}
Current Narration:
"{current_narration}"

## Feedback:
"{feedback_text}"

## Interpretation:
{interpretation}

## Narration Quality Guidelines
When revising narration, follow these principles:

1. USE SPECIFIC NUMBERS instead of vague qualifiers
   - BAD: "improved dramatically", "much better", "significant improvement"
   - GOOD: "jumped from 17% to 78%", "one hundred times more often", "500-token chain"
   - Pull exact figures from the source material whenever possible

2. EXPLAIN MECHANISMS step-by-step (HOW, not just THAT)
   - BAD: "Tree-of-thought search explores multiple reasoning paths"
   - GOOD: "Tree-of-thought works like this: generate three candidates, evaluate each, expand the best one. Hit a dead end? Backtrack and try another branch."
   - Break down processes into sequential steps viewers can follow

3. CREATE INFORMATION GAPS before revealing solutions
   - Start with "Here's the problem:" or "Here's the challenge:" before giving the answer
   - Build tension: present the obstacle, THEN reveal the solution

4. CONNECT CAUSALLY with transitions
   - Use "But there's a problem...", "The breakthrough came when...", "This leads to..."
   - Each scene should flow naturally into the next

## Instructions
Generate specific text changes. Be precise about what to change.
Apply the narration quality guidelines above to improve the narration.

Respond with JSON:
{{
    "changes": [
        {{
            "field": "voiceover",  // or "title"
            "old_text": "exact text to find (or null for additions)",
            "new_text": "replacement text",
            "reason": "why this change addresses the feedback"
        }}
    ]
}}
"""


GENERATE_VISUAL_CUE_PATCH_PROMPT = """Generate patches to update the visual_cue specification.

## Scene Information
Scene ID: {scene_id}
Scene Title: {scene_title}
Scene Type: {scene_type}
Narration: "{narration}"

## Current Visual Cue:
{current_visual_cue}

## Feedback:
"{feedback_text}"

## Interpretation:
{interpretation}

## Visual Styling Guidelines
- BACKGROUND: Scene canvas/backdrop - use LIGHT colors (#f0f0f5, #fafafa, #ffffff)
- UI COMPONENTS: Floating dark glass panels with:
  - Dark glass: rgba(18,20,25,0.98) backgrounds
  - Multi-layer shadows (5-7 layers) for depth
  - Bezel borders: light top/left, dark bottom/right
  - Inner shadows for recessed depth
  - Colored accent glows based on content

## Text Styling (CRITICAL)
- All text on dark panels MUST be white (#ffffff) or light gray
- NEVER use black/dark text on dark backgrounds - it will be invisible
- Minimum font sizes: titles 22-28px, body 16-18px, annotations 14-16px

## Layout Constraints
- Content panels start at LAYOUT.title.y + 140 (not crowding the header)
- Leave 100px at bottom for Reference component
- All labels/badges must stay INSIDE their containers (no overflow)
- Gap between panels: 25-50px

## Instructions
Generate an improved visual_cue that addresses the feedback while following styling guidelines.

Respond with JSON:
{{
    "needs_update": true,
    "new_visual_cue": {{
        "description": "BACKGROUND: [describe backdrop]. UI COMPONENTS: [describe panels].",
        "visual_type": "animation",
        "elements": [
            "BACKGROUND: description",
            "UI Component 1 with styling details",
            "UI Component 2 with styling details"
        ],
        "duration_seconds": {duration}
    }},
    "reason": "Why this change addresses the feedback"
}}
"""


GENERATE_STRUCTURE_PATCH_PROMPT = """Generate patches to modify the scene structure.

## Current Scenes:
{scene_list}

## Feedback:
"{feedback_text}"

## Interpretation:
{interpretation}

## Instructions
Determine what structural changes are needed:
- Adding a new scene (provide title, narration, visual description)
- Removing a scene (specify which one)
- Reordering scenes (provide new order)

Respond with JSON:
{{
    "action": "add|remove|reorder",
    "details": {{
        // For "add":
        "insert_after": "scene_id or null for beginning",
        "new_scene": {{
            "title": "Scene Title",
            "scene_type": "hook|context|explanation|insight|conclusion",
            "narration": "The voiceover text...",
            "visual_description": "What should be visualized",
            "duration_seconds": 25
        }},
        // For "remove":
        "scene_id": "scene_to_remove",
        // For "reorder":
        "new_order": ["scene_id_1", "scene_id_2", ...]
    }},
    "reason": "Why this structural change addresses the feedback"
}}
"""
