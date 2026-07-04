# Design: Unified Feedback System in `src/refine/`

## Overview

This document outlines the design for deprecating `src/feedback/` and reimplementing feedback functionality from first principles in `src/refine/`. The new system takes concrete text feedback and automatically applies changes to script, narration, and visuals.

---

## Current State Analysis

### Problems with `src/feedback/`

1. **Generic Approach**: Doesn't distinguish between script, visual, or structural changes - gives LLM free reign
2. **No Structured Patches**: Changes aren't represented as reviewable patches
3. **No Verification**: Changes aren't validated after application
4. **Hardcoded Paths**: Prompts contain hardcoded paths (`llm-inference`)
5. **Disconnected**: Separate from refinement system, doesn't share models/infrastructure
6. **Limited History**: Basic status tracking without detailed change records

### Strengths of `src/refine/`

1. **Structured Patches**: Well-defined patch types (AddScenePatch, ModifyScenePatch, etc.)
2. **Specialized Processors**: Phase-specific analyzers with targeted prompts
3. **Validation**: Project sync validation before changes
4. **Verification**: Visual inspection with screenshot verification
5. **Principles-Based**: 13 guiding principles for quality assessment

---

## Design Goals

1. **Unified Infrastructure**: One system for both systematic refinement and ad-hoc feedback
2. **Structured Changes**: All changes represented as reviewable patches
3. **Multi-Target**: Support changes to script, narration, visual_cues, and scene components
4. **Verification**: Validate changes after application
5. **History**: Track all feedback with detailed change records
6. **Interactive**: Support for dry-run, preview, and approval workflows

---

## Architecture

```
src/refine/
├── feedback/                      # NEW: Feedback module
│   ├── __init__.py
│   ├── models.py                  # Feedback data models
│   ├── parser.py                  # Parse feedback text → intent + targets
│   ├── generator.py               # Generate patches from feedback
│   ├── applicator.py              # Apply patches with verification
│   ├── store.py                   # Persist feedback history
│   └── prompts.py                 # LLM prompts for feedback processing
├── models.py                      # Existing patch models (extend)
├── command.py                     # Add `feedback` subcommand
└── ...
```

---

## Data Models

### FeedbackIntent (NEW)

Classifies what the feedback is asking to change:

```python
class FeedbackIntent(Enum):
    """What kind of change the feedback requests."""
    SCRIPT_CONTENT = "script_content"      # Change what's said (narration text)
    SCRIPT_STRUCTURE = "script_structure"  # Add/remove/reorder scenes
    VISUAL_CUE = "visual_cue"              # Change visual specification
    VISUAL_IMPLEMENTATION = "visual_impl"  # Change scene component code
    TIMING = "timing"                       # Adjust scene durations
    STYLE = "style"                         # Change visual styling patterns
    MIXED = "mixed"                         # Multiple types of changes
```

### FeedbackTarget (NEW)

Identifies which scenes/files are affected:

```python
@dataclass
class FeedbackTarget:
    """Where the feedback should be applied."""
    scene_ids: list[int]              # Which scenes (1-indexed)
    files: list[Path]                  # Specific files to modify
    scope: FeedbackScope               # SCENE, MULTI_SCENE, PROJECT
```

### FeedbackItem (ENHANCED from existing)

```python
@dataclass
class FeedbackItem:
    """A single feedback item with its processing state."""
    id: str                            # Unique ID (fb_XXXX_timestamp)
    timestamp: datetime
    feedback_text: str                 # Original user input
    status: FeedbackStatus             # PENDING, ANALYZING, APPLYING, APPLIED, FAILED

    # Analysis results
    intent: FeedbackIntent | None
    target: FeedbackTarget | None
    interpretation: str                # What the LLM understood

    # Generated patches
    patches: list[ScriptPatch]         # Reuse existing patch types

    # Application results
    files_modified: list[str]
    verification_result: dict | None
    error_message: str | None
```

### Extend Existing Patches

Add new patch type for visual implementation changes:

```python
@dataclass
class VisualImplementationPatch(ScriptPatch):
    """Patch for modifying scene component code."""
    patch_type: ScriptPatchType = ScriptPatchType.VISUAL_IMPLEMENTATION
    scene_id: int
    scene_file: Path
    description: str                   # What change to make
    code_changes: list[CodeEdit]       # Specific edits

@dataclass
class CodeEdit:
    """A single code edit operation."""
    file_path: Path
    edit_type: Literal["replace", "insert", "delete"]
    old_content: str | None            # For replace/delete
    new_content: str | None            # For replace/insert
    location: str                      # Description of where (e.g., "in COLORS object")
```

---

## Processing Pipeline

### Phase 1: Parse Feedback

```
User Input: "Make the numbers in scene 1 bigger and change the background to dark blue"
                                    ↓
                            FeedbackParser
                                    ↓
FeedbackItem {
    intent: MIXED (VISUAL_IMPLEMENTATION + VISUAL_CUE),
    target: {scene_ids: [1], scope: SCENE},
    interpretation: "User wants larger number text and darker background in scene 1"
}
```

### Phase 2: Generate Patches

```
FeedbackItem → PatchGenerator → list[ScriptPatch]

Patches:
1. UpdateVisualCuePatch {
     scene_id: 1,
     current_visual_cue: {...},
     new_visual_cue: {description: "BACKGROUND: Dark blue gradient..."}
   }

2. VisualImplementationPatch {
     scene_id: 1,
     scene_file: "scenes/TheImpossibleLeapScene.tsx",
     code_changes: [
       {edit_type: "replace", old: "fontSize: 48", new: "fontSize: 72"}
     ]
   }
```

### Phase 3: Apply with Verification

```
Patches → PatchApplicator → Applied Changes
                ↓
         Verification (optional)
                ↓
         FeedbackItem.status = APPLIED
```

---

## Key Components

### 1. FeedbackParser

Analyzes feedback text to determine intent and target.

```python
class FeedbackParser:
    """Parses user feedback into structured intent and targets."""

    def parse(self, feedback_text: str, project: Project) -> FeedbackItem:
        """
        Parse feedback text into a structured FeedbackItem.

        Uses LLM to:
        1. Identify what kind of change (intent)
        2. Determine which scenes/files are affected (target)
        3. Generate interpretation
        """
        ...
```

**Prompt Strategy**:
- Provide project context (scene list, structure)
- Ask LLM to classify intent from predefined categories
- Extract specific scene references from text
- Generate clear interpretation

### 2. PatchGenerator

Generates appropriate patches based on feedback intent.

```python
class PatchGenerator:
    """Generates patches from parsed feedback."""

    def generate(self, item: FeedbackItem, project: Project) -> list[ScriptPatch]:
        """
        Generate patches based on feedback intent.

        Routes to specialized generators:
        - SCRIPT_CONTENT → generate_narration_patches()
        - VISUAL_CUE → generate_visual_cue_patches()
        - VISUAL_IMPLEMENTATION → generate_code_patches()
        - etc.
        """
        ...
```

**Specialized Generators**:

| Intent | Generator | Output Patch Type |
|--------|-----------|-------------------|
| SCRIPT_CONTENT | `_generate_narration_patches()` | ModifyScenePatch |
| SCRIPT_STRUCTURE | `_generate_structure_patches()` | AddScenePatch, DeleteScenePatch |
| VISUAL_CUE | `_generate_visual_cue_patches()` | UpdateVisualCuePatch |
| VISUAL_IMPLEMENTATION | `_generate_code_patches()` | VisualImplementationPatch |
| TIMING | `_generate_timing_patches()` | ModifyScenePatch (duration) |

### 3. PatchApplicator

Applies patches and optionally verifies results.

```python
class PatchApplicator:
    """Applies patches to project files."""

    def apply(
        self,
        patches: list[ScriptPatch],
        project: Project,
        verify: bool = False,
    ) -> ApplicationResult:
        """
        Apply patches to project files.

        For each patch type:
        - ModifyScenePatch → Update narrations.json and script.json
        - UpdateVisualCuePatch → Update script.json visual_cue
        - VisualImplementationPatch → Use Claude Code to edit .tsx files

        If verify=True:
        - For visual changes: Take screenshot and verify improvement
        - For script changes: Validate JSON structure
        """
        ...
```

### 4. FeedbackStore

Persists feedback history.

```python
class FeedbackStore:
    """Stores feedback history for a project."""

    # Location: projects/{project-id}/refinement/feedback.json

    def add(self, item: FeedbackItem) -> None: ...
    def update(self, item: FeedbackItem) -> None: ...
    def get(self, item_id: str) -> FeedbackItem | None: ...
    def list_all(self) -> list[FeedbackItem]: ...
    def list_by_status(self, status: FeedbackStatus) -> list[FeedbackItem]: ...
```

---

## CLI Integration

### New Command: `feedback`

```bash
# Add and process feedback
python -m src.cli.main feedback thinking-models "Make the numbers bigger in scene 1"

# With options
python -m src.cli.main feedback thinking-models "..." --dry-run      # Analyze without applying
python -m src.cli.main feedback thinking-models "..." --verify       # Verify after applying
python -m src.cli.main feedback thinking-models "..." --interactive  # Approve patches one-by-one

# List feedback history
python -m src.cli.main feedback thinking-models --list
python -m src.cli.main feedback thinking-models --list --status applied

# Show specific feedback
python -m src.cli.main feedback thinking-models --show fb_0001_20260121
```

### Command Arguments

```python
def add_feedback_parser(subparsers):
    parser = subparsers.add_parser(
        "feedback",
        help="Apply feedback to a video project",
    )

    parser.add_argument("project", help="Project ID")
    parser.add_argument("text", nargs="?", help="Feedback text")

    # Mode options
    parser.add_argument("--dry-run", action="store_true",
        help="Analyze feedback and show patches without applying")
    parser.add_argument("--verify", action="store_true",
        help="Verify changes after applying (take screenshots)")
    parser.add_argument("--interactive", "-i", action="store_true",
        help="Approve each patch before applying")

    # History options
    parser.add_argument("--list", action="store_true",
        help="List all feedback for this project")
    parser.add_argument("--show", metavar="ID",
        help="Show details of specific feedback item")
    parser.add_argument("--status", choices=["pending", "applied", "failed"],
        help="Filter by status when listing")
```

---

## Prompts

### Parse Feedback Prompt

```python
PARSE_FEEDBACK_PROMPT = """Analyze this user feedback for a video project.

## Project: {project_id}
## Available Scenes:
{scene_list}

## User Feedback:
"{feedback_text}"

## Instructions
Determine:
1. What KIND of change is being requested (intent)
2. Which SCENES are affected
3. What the user MEANS (interpretation)

## Intent Categories
- script_content: Changing what is SAID in the narration
- script_structure: Adding, removing, or reordering SCENES
- visual_cue: Changing the DESCRIPTION of what should be visualized
- visual_impl: Changing the ACTUAL CODE that renders the scene
- timing: Adjusting scene DURATIONS
- style: Changing visual STYLING patterns (colors, shadows, etc.)
- mixed: Multiple types of changes

Respond with JSON:
{{
    "intent": "script_content|script_structure|visual_cue|visual_impl|timing|style|mixed",
    "affected_scene_ids": [1, 2, ...],
    "scope": "scene|multi_scene|project",
    "interpretation": "Clear description of what the user wants",
    "sub_intents": ["intent1", "intent2"]  // Only if mixed
}}
"""
```

### Generate Code Patches Prompt

```python
GENERATE_CODE_PATCHES_PROMPT = """Generate code changes for this visual feedback.

## Scene: {scene_title} (Scene {scene_id})
## Scene File: {scene_file}

## Current Implementation:
```tsx
{current_code}
```

## Feedback:
"{feedback_text}"

## Interpretation:
{interpretation}

## Visual Styling Patterns (use these):
- Dark glass: rgba(18,20,25,0.98) backgrounds
- Multi-layer shadows: 5-7 layers for depth
- Bezel borders: light top/left, dark bottom/right
- Font sizes: 24px+ body, 48px+ headlines

Generate specific code edits:
{{
    "changes": [
        {{
            "description": "What this change does",
            "edit_type": "replace|insert|delete",
            "old_content": "exact text to find",
            "new_content": "replacement text",
            "location": "where in the file (e.g., 'in COLORS object')"
        }}
    ],
    "reasoning": "Why these changes address the feedback"
}}
"""
```

---

## Workflow Examples

### Example 1: Simple Narration Change

```
User: "In scene 3, say 'reasoning process' instead of 'thinking process'"

Parse → intent: SCRIPT_CONTENT, scenes: [3]
Generate → ModifyScenePatch(scene_id=3, field="voiceover", old="thinking process", new="reasoning process")
Apply → Updates script.json and narrations.json
```

### Example 2: Visual Style Change

```
User: "Make the background in scene 1 darker"

Parse → intent: VISUAL_CUE + VISUAL_IMPL, scenes: [1]
Generate → [
    UpdateVisualCuePatch(scene_id=1, new_visual_cue={...}),
    VisualImplementationPatch(scene_id=1, code_changes=[...])
]
Apply → Updates script.json, then edits Scene1.tsx
Verify → Takes screenshot to confirm darker background
```

### Example 3: Structural Change

```
User: "Add a new scene after scene 2 explaining gradient descent"

Parse → intent: SCRIPT_STRUCTURE, affected_scenes: [2]
Generate → AddScenePatch(
    insert_after_scene_id=2,
    new_scene_id=3,
    title="Understanding Gradient Descent",
    narration="...",
    visual_description="..."
)
Apply → Updates script.json and narrations.json, shifts scene IDs
```

---

## Migration Plan

### Phase 1: Build New System
1. Create `src/refine/feedback/` module
2. Implement FeedbackParser
3. Implement PatchGenerator (reuse existing patch types)
4. Implement PatchApplicator
5. Implement FeedbackStore
6. Add CLI command

### Phase 2: Testing
1. Test with simple narration changes
2. Test with visual_cue changes
3. Test with code changes
4. Test with structural changes
5. Test dry-run and interactive modes

### Phase 3: Deprecation
1. Add deprecation warning to `src/feedback/` imports
2. Update any code that uses old feedback system
3. Remove `src/feedback/` after confirmation period

---

## File Changes Summary

### New Files
- `src/refine/feedback/__init__.py`
- `src/refine/feedback/models.py`
- `src/refine/feedback/parser.py`
- `src/refine/feedback/generator.py`
- `src/refine/feedback/applicator.py`
- `src/refine/feedback/store.py`
- `src/refine/feedback/prompts.py`

### Modified Files
- `src/refine/models.py` - Add VisualImplementationPatch, ScriptPatchType.VISUAL_IMPLEMENTATION
- `src/refine/command.py` - Add `cmd_feedback()` and argument parser
- `src/cli/main.py` - Register feedback command

### Deprecated Files (to remove later)
- `src/feedback/__init__.py`
- `src/feedback/models.py`
- `src/feedback/processor.py`
- `src/feedback/prompts.py`
- `src/feedback/store.py`

---

## Decisions

1. **Verification Scope**: Visual verification is **mandatory** for any scene changes.

2. **Patch Granularity**: Let Claude Code figure out code changes. Ensure it can use the `/remotion` skill for visual styling patterns.

3. **History Location**: Store in `projects/{id}/refinement/feedback.json`.

4. **Rollback Support**: Skip - rely on git for version control.

---

## Scene ID Management (Simplified)

### New Unified Format

Scene IDs are now **slug-based strings** everywhere (no numeric prefixes):

| File | ID Format | Example |
|------|-----------|---------|
| `storyboard.json` | Slug string | `"the_impossible_leap"` |
| `script.json` | Slug string | `"the_impossible_leap"` |
| `narrations.json` | Slug string | `"the_impossible_leap"` |
| `voiceover/manifest.json` | Slug string | `"the_impossible_leap"` |
| Audio files | Slug filename | `the_impossible_leap.mp3` |
| Scene components | PascalCase | `TheImpossibleLeapScene.tsx` |
| Registry keys | snake_case | `impossible_leap` |

**Benefits of this simplification:**
- **No renumbering needed**: Order is determined by array position, not embedded in ID
- **Consistent format**: Same slug format everywhere
- **Easier to manage**: Adding/removing scenes doesn't require ID changes

### Files to Update When Adding a Scene

1. **Create scene component**: `projects/{project}/scenes/NewScene.tsx`
2. **Update registry**: `projects/{project}/scenes/index.ts`
   - Import the component
   - Add to `SCENE_REGISTRY`
   - Export the component
3. **Update storyboard**: `storyboard/storyboard.json`
   - Add scene object with `id`, `type`, `audio_file`, `audio_duration_seconds`
   - Update `total_duration_seconds`
4. **Create voiceover**: `voiceover/scene{N}_{slug}.mp3`
5. **Update manifest**: `voiceover/manifest.json`
6. **Update narrations**: `narration/narrations.json`
7. **Update script**: `script/script.json` (renumber all subsequent `scene_id` values)

### Files to Update When Removing a Scene

1. Delete scene component file
2. Remove from `scenes/index.ts` (import, registry, export)
3. Remove from `storyboard/storyboard.json`
4. Delete audio file
5. Remove from `voiceover/manifest.json`
6. Remove from `narration/narrations.json`
7. Remove from `script/script.json` (renumber all subsequent `scene_id` values)
8. Remove refinement outputs if they exist

### Key Insight: The Type Field is the Link

The `type` field in `storyboard.json` (e.g., `"thinking-models/impossible_leap"`) maps to registry keys. This decouples scene ordering from component identity.

```
storyboard.json (type: "thinking-models/impossible_leap")
         ↓
    SCENE_REGISTRY["impossible_leap"]
         ↓
    TheImpossibleLeapScene component
```

### Implementation: SceneManager Helper

With the simplified ID format, scene management is much easier:

```python
class SceneManager:
    """Manages scene consistency across all project files."""

    def __init__(self, project: Project):
        self.project = project

    def add_scene(
        self,
        after_scene_id: str | None,  # None = add at beginning
        title: str,
        narration: str,
        visual_cue: dict,
        duration_seconds: float,
    ) -> AddSceneResult:
        """
        Add a new scene after the specified scene.

        Updates all required files:
        - storyboard.json (insert at position)
        - narrations.json (insert at position)
        - script.json (insert at position)
        - scenes/index.ts (placeholder component)

        No ID renumbering needed - order is determined by array position.
        """
        scene_id = self._slugify(title)
        # Insert into all files at correct position
        ...

    def remove_scene(self, scene_id: str) -> RemoveSceneResult:
        """Remove a scene. No renumbering needed."""
        ...

    def reorder_scenes(self, new_order: list[str]) -> ReorderResult:
        """Reorder scenes. Just reorder arrays in all files."""
        ...

    def _slugify(self, title: str) -> str:
        """Generate slug from title: 'The Impossible Leap' -> 'the_impossible_leap'."""
        ...
```

---

## Summary

The new feedback system:
- Integrates with existing refinement infrastructure
- Uses structured patches for all changes
- Supports script, narration, visual_cue, and visual implementation changes
- Provides dry-run, interactive, and verification modes
- Maintains detailed history of all feedback
- Deprecates the old `src/feedback/` module

This design leverages the strengths of the existing refinement system while providing the flexibility needed for ad-hoc user feedback.
