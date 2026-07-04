"""Sound design module for video explainer.

This module provides intelligent SFX generation for frame-accurate sound design.

The sound design workflow is:
1. Analyze scene code for animation patterns
   - TypeScript AST analyzer (ts_analyzer) for accurate expression evaluation
   - Regex-based analyzer (scene_analyzer) as fallback
2. Apply semantic sound mapping (semantic_mapper)
3. Sync to narration word timestamps (narration_sync)
4. Optional LLM semantic analysis (llm_analyzer)
5. Aggregate and filter moments (aggregator)
6. Generate SFX cues (cue_generator)
7. Update storyboard.json (storyboard_updater)
8. Generate SFX files using SoundLibrary
9. Remotion renders video with SFX at specified frames

Components:
- models: Data structures (SoundMoment, SFXCue)
- library: SFX generation with 17 focused sounds
- generator: Theme-aware sound synthesis
- ts_analyzer: TypeScript AST-based animation extraction
- scene_analyzer: Regex-based TSX code pattern detection (fallback)
- semantic_mapper: Context-aware sound selection
- narration_sync: Word timestamp sync
- llm_analyzer: LLM semantic analysis
- aggregator: Moment deduplication and filtering
- cue_generator: Moment to cue mapping
- storyboard_updater: Storyboard modification
- sfx_orchestrator: Main pipeline orchestrator
"""

from .library import SoundLibrary, SOUND_MANIFEST
from .models import (
    SoundMoment,
    SFXCue,
    WordTimestamp,
    SceneAnalysisResult,
    MomentType,
    calculate_volume,
    get_sound_for_moment,
)
from .generator import SoundGenerator, SoundEvent, SoundTheme
from .ts_analyzer import TypeScriptAnalyzer, analyze_scene_with_ast
from .scene_analyzer import SceneAnalyzer, analyze_scene, find_scene_files
from .semantic_mapper import SemanticSoundMapper, map_moment_to_sound, map_moments_to_sounds
from .narration_sync import (
    NarrationSyncAnalyzer,
    sync_to_narration,
    analyze_narration_text,
)
from .aggregator import aggregate_moments, get_density_report
from .cue_generator import CueGenerator, SceneSFXGenerator
from .storyboard_updater import StoryboardUpdater, update_storyboard, load_storyboard
from .sfx_orchestrator import (
    SFXOrchestrator,
    SFXGenerationResult,
    generate_project_sfx,
    analyze_project_scenes,
)

__all__ = [
    # Models
    "SoundMoment",
    "SFXCue",
    "WordTimestamp",
    "SceneAnalysisResult",
    "MomentType",
    "calculate_volume",
    "get_sound_for_moment",
    # Library
    "SoundLibrary",
    "SOUND_MANIFEST",
    # Generator
    "SoundGenerator",
    "SoundEvent",
    "SoundTheme",
    # TypeScript AST Analyzer
    "TypeScriptAnalyzer",
    "analyze_scene_with_ast",
    # Scene Analyzer (regex fallback)
    "SceneAnalyzer",
    "analyze_scene",
    "find_scene_files",
    # Semantic Mapper
    "SemanticSoundMapper",
    "map_moment_to_sound",
    "map_moments_to_sounds",
    # Narration Sync
    "NarrationSyncAnalyzer",
    "sync_to_narration",
    "analyze_narration_text",
    # Aggregator
    "aggregate_moments",
    "get_density_report",
    # Cue Generator
    "CueGenerator",
    "SceneSFXGenerator",
    # Storyboard Updater
    "StoryboardUpdater",
    "update_storyboard",
    "load_storyboard",
    # Orchestrator
    "SFXOrchestrator",
    "SFXGenerationResult",
    "generate_project_sfx",
    "analyze_project_scenes",
]
