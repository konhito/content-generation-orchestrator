"""SFX Orchestrator - Main pipeline for generating sound effects.

This module coordinates the full SFX generation pipeline:
1. Load storyboard and scene information
2. Analyze scene code for animation patterns (TypeScript AST or regex fallback)
3. Apply semantic sound mapping based on context
4. (Optional) Sync to narration word timestamps
5. (Optional) LLM semantic analysis
6. Aggregate and deduplicate moments
7. Generate SFX cues
8. Update storyboard.json
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .models import SoundMoment, SFXCue, SceneAnalysisResult
from .scene_analyzer import SceneAnalyzer, find_scene_files
from .ts_analyzer import TypeScriptAnalyzer
from .semantic_mapper import SemanticSoundMapper
from .cue_generator import CueGenerator, SceneSFXGenerator
from .storyboard_updater import StoryboardUpdater, load_storyboard
from .aggregator import aggregate_moments
from .generator import SoundTheme


@dataclass
class SFXGenerationResult:
    """Result of SFX generation for a project."""

    project_id: str
    scenes_analyzed: int
    moments_detected: int
    cues_generated: int
    scenes_updated: dict[str, bool]
    errors: list[str]

    @property
    def success(self) -> bool:
        """Check if generation was successful."""
        return not self.errors and all(self.scenes_updated.values())


class SFXOrchestrator:
    """Orchestrates the full SFX generation pipeline.

    Coordinates scene analysis, moment detection, cue generation,
    and storyboard updates. Uses TypeScript AST analysis for accurate
    frame timing extraction with regex fallback.
    """

    def __init__(
        self,
        project_dir: Path,
        theme: SoundTheme = SoundTheme.TECH_AI,
        fps: int = 30,
        use_library: bool = True,
        use_ast_analyzer: bool = True,
    ):
        """Initialize the orchestrator.

        Args:
            project_dir: Path to the project directory
            theme: Sound theme for generation
            fps: Frames per second (default 30)
            use_library: Use library sounds vs custom generation
            use_ast_analyzer: Use TypeScript AST analyzer (falls back to regex)
        """
        self.project_dir = Path(project_dir)
        self.theme = theme
        self.fps = fps
        self.use_library = use_library
        self.use_ast_analyzer = use_ast_analyzer

        # Determine paths
        self.storyboard_path = self.project_dir / "storyboard" / "storyboard.json"
        self.sfx_dir = self.project_dir / "sfx"

        # Components - both analyzers available
        self.regex_analyzer = SceneAnalyzer(fps=fps)
        self.ts_analyzer = TypeScriptAnalyzer(fps=fps) if use_ast_analyzer else None
        self.semantic_mapper = SemanticSoundMapper()
        self.cue_generator = CueGenerator(
            use_library=use_library,
            theme=theme,
            sfx_dir=self.sfx_dir,
        )

    def _find_remotion_dir(self) -> Path:
        """Find the remotion directory relative to project."""
        # Try common locations
        candidates = [
            self.project_dir.parent.parent / "remotion",
            self.project_dir.parent / "remotion",
            Path.cwd() / "remotion",
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate

        raise FileNotFoundError("Could not find remotion directory")

    def _find_scene_file(self, scene_type: str, project_id: str) -> Optional[Path]:
        """Find the scene TSX file for a given scene type.

        Scenes can be in multiple locations:
        1. projects/<project>/scenes/<SceneName>.tsx
        2. remotion/src/scenes/<project>/<scene>.tsx

        Args:
            scene_type: Scene type path (e.g., "llm-inference/hook")
            project_id: Project identifier

        Returns:
            Path to scene file if found, None otherwise
        """
        # Extract scene name from type
        scene_name = scene_type.split("/")[-1] if "/" in scene_type else scene_type
        pascal_name = self._to_pascal_case(scene_name)

        # Try project's scenes directory first
        project_scenes_dir = self.project_dir / "scenes"
        if project_scenes_dir.exists():
            # Try various naming conventions
            candidates = [
                project_scenes_dir / f"{scene_name}.tsx",
                project_scenes_dir / f"{scene_name.title()}Scene.tsx",
                project_scenes_dir / f"{pascal_name}Scene.tsx",
                # Also try with "The" prefix (common convention)
                project_scenes_dir / f"The{pascal_name}Scene.tsx",
            ]
            for candidate in candidates:
                if candidate.exists():
                    return candidate

            # Also try searching by partial match (remove underscores/hyphens for comparison)
            scene_name_normalized = scene_name.lower().replace("_", "").replace("-", "")
            for file in project_scenes_dir.glob("*.tsx"):
                file_stem_normalized = file.stem.lower().replace("_", "").replace("-", "")
                if scene_name_normalized in file_stem_normalized:
                    return file

        # Try remotion directory
        try:
            remotion_dir = self._find_remotion_dir()
            scenes_dir = remotion_dir / "src" / "scenes" / project_id

            if scenes_dir.exists():
                candidate = scenes_dir / f"{scene_name}.tsx"
                if candidate.exists():
                    return candidate
        except FileNotFoundError:
            pass

        return None

    def _to_pascal_case(self, name: str) -> str:
        """Convert snake_case or kebab-case to PascalCase."""
        # Handle kebab-case
        name = name.replace("-", "_")
        # Convert to PascalCase
        return "".join(word.title() for word in name.split("_"))

    def _get_project_id(self) -> str:
        """Extract project ID from storyboard or directory."""
        if self.storyboard_path.exists():
            updater = load_storyboard(self.storyboard_path)
            return updater.get_project_info().get("project", self.project_dir.name)
        return self.project_dir.name

    def analyze_scenes(
        self,
        scene_types: Optional[list[str]] = None,
    ) -> dict[str, SceneAnalysisResult]:
        """Analyze all scene files and detect animation patterns.

        Uses TypeScript AST analyzer for accurate frame timing extraction,
        with automatic fallback to regex-based analysis if AST parsing fails.

        Args:
            scene_types: Optional list of scene types to analyze.
                        If None, analyzes all scenes in storyboard.

        Returns:
            Dict mapping scene IDs to analysis results
        """
        results = {}

        # Load storyboard to get scene information
        if not self.storyboard_path.exists():
            raise FileNotFoundError(f"Storyboard not found: {self.storyboard_path}")

        updater = load_storyboard(self.storyboard_path)
        project_id = updater.get_project_info().get("project", "")

        for scene in updater.get_scenes():
            scene_id = scene.get("id", "")
            scene_type = scene.get("type", "")

            # Filter if specific scene types requested
            if scene_types and scene_type not in scene_types:
                continue

            # Get duration from storyboard
            duration_frames = int(scene.get("audio_duration_seconds", 10) * self.fps)

            # Try to find the scene file
            scene_file = self._find_scene_file(scene_type, project_id)

            # Create analysis result
            if scene_file:
                result = self._analyze_scene_file(
                    scene_file, scene_id, scene_type, duration_frames
                )
                results[scene_id] = result
            else:
                # No scene file found - create empty result
                results[scene_id] = SceneAnalysisResult(
                    scene_id=scene_id,
                    scene_type=scene_type,
                    duration_frames=duration_frames,
                    analysis_notes=["Scene file not found"],
                )

        return results

    def _analyze_scene_file(
        self,
        scene_file: Path,
        scene_id: str,
        scene_type: str,
        duration_frames: int,
    ) -> SceneAnalysisResult:
        """Analyze a single scene file with AST analyzer and regex fallback.

        Args:
            scene_file: Path to the TSX file
            scene_id: Scene identifier
            scene_type: Scene type string
            duration_frames: Duration in frames

        Returns:
            SceneAnalysisResult with detected moments
        """
        result = None
        analysis_notes = []

        # Try TypeScript AST analyzer first (if enabled)
        if self.use_ast_analyzer and self.ts_analyzer:
            try:
                result = self.ts_analyzer.analyze_scene(scene_file, duration_frames)
                analysis_notes.append("Analyzed with TypeScript AST parser")
            except Exception as e:
                analysis_notes.append(f"AST analysis failed: {e}, falling back to regex")

        # Fall back to regex analyzer
        if result is None or not result.moments:
            try:
                result = self.regex_analyzer.analyze_scene(scene_file)
                if not analysis_notes or "falling back" in analysis_notes[-1]:
                    analysis_notes.append("Analyzed with regex patterns")
            except Exception as e:
                # Create empty result with error
                result = SceneAnalysisResult(
                    scene_id=scene_id,
                    scene_type=scene_type,
                    duration_frames=duration_frames,
                    analysis_notes=[f"Analysis error: {e}"],
                )
                return result

        # Update result with correct metadata
        result.scene_id = scene_id
        result.scene_type = scene_type
        result.source_file = str(scene_file)
        result.duration_frames = duration_frames
        result.analysis_notes.extend(analysis_notes)

        # Apply semantic sound mapping to all moments
        for moment in result.moments:
            selection = self.semantic_mapper.select_sound(moment, duration_frames)
            # Store the mapped sound in the context for later use
            moment.context = f"{moment.context} [mapped: {selection.sound}]"

        return result

    def generate_sfx_cues(
        self,
        use_llm: bool = False,
        dry_run: bool = False,
        max_per_second: float = 3.0,
        min_gap_frames: int = 10,
    ) -> SFXGenerationResult:
        """Generate SFX cues for the entire project.

        Args:
            use_llm: Whether to use LLM for semantic analysis
            dry_run: If True, don't write to storyboard
            max_per_second: Maximum sound density
            min_gap_frames: Minimum frames between sounds

        Returns:
            SFXGenerationResult with statistics
        """
        errors = []
        project_id = self._get_project_id()

        # Step 1: Analyze scenes
        try:
            analyses = self.analyze_scenes()
        except FileNotFoundError as e:
            return SFXGenerationResult(
                project_id=project_id,
                scenes_analyzed=0,
                moments_detected=0,
                cues_generated=0,
                scenes_updated={},
                errors=[str(e)],
            )

        # Step 2: Aggregate moments for each scene
        all_cues: dict[str, list[SFXCue]] = {}
        total_moments = 0
        total_cues = 0

        for scene_id, analysis in analyses.items():
            # Get moments from code analysis
            code_moments = analysis.moments.copy()

            # TODO: Add narration sync moments
            narration_moments: list[SoundMoment] = []

            # TODO: Add LLM analysis moments
            llm_moments: list[SoundMoment] = []

            # Aggregate all sources
            aggregated = aggregate_moments(
                code_moments=code_moments,
                narration_moments=narration_moments,
                llm_moments=llm_moments,
                max_per_second=max_per_second,
                min_gap_frames=min_gap_frames,
                fps=self.fps,
            )

            total_moments += len(analysis.moments)

            # Generate cues
            cues = self.cue_generator.generate_cues(aggregated, scene_id)
            all_cues[scene_id] = cues
            total_cues += len(cues)

        # Step 3: Update storyboard (unless dry run)
        scenes_updated = {}
        if not dry_run:
            try:
                updater = load_storyboard(self.storyboard_path)
                scenes_updated = updater.update_all_scenes(all_cues, mode="replace")
                updater.save(backup=True)
            except Exception as e:
                errors.append(f"Failed to update storyboard: {e}")

        return SFXGenerationResult(
            project_id=project_id,
            scenes_analyzed=len(analyses),
            moments_detected=total_moments,
            cues_generated=total_cues,
            scenes_updated=scenes_updated,
            errors=errors,
        )

    def preview_analysis(self) -> dict:
        """Preview analysis results without generating cues.

        Returns:
            Dict with analysis summary per scene
        """
        analyses = self.analyze_scenes()

        preview = {}
        for scene_id, analysis in analyses.items():
            moments_by_type = {}
            for moment in analysis.moments:
                if moment.type not in moments_by_type:
                    moments_by_type[moment.type] = 0
                moments_by_type[moment.type] += 1

            preview[scene_id] = {
                "scene_type": analysis.scene_type,
                "duration_frames": analysis.duration_frames,
                "total_moments": len(analysis.moments),
                "moments_by_type": moments_by_type,
                "notes": analysis.analysis_notes,
            }

        return preview

    def get_scene_moments(self, scene_id: str) -> list[SoundMoment]:
        """Get detected moments for a specific scene.

        Args:
            scene_id: Scene identifier

        Returns:
            List of SoundMoment objects
        """
        analyses = self.analyze_scenes()
        if scene_id in analyses:
            return analyses[scene_id].moments
        return []


def generate_project_sfx(
    project_dir: Path,
    use_llm: bool = False,
    dry_run: bool = False,
    theme: str = "tech_ai",
    use_library: bool = True,
) -> SFXGenerationResult:
    """Generate SFX cues for a project.

    Convenience function for the full pipeline.

    Args:
        project_dir: Path to project directory
        use_llm: Whether to use LLM analysis
        dry_run: If True, don't write to storyboard
        theme: Sound theme name
        use_library: Use library sounds vs custom

    Returns:
        SFXGenerationResult
    """
    theme_enum = SoundTheme(theme) if theme in [t.value for t in SoundTheme] else SoundTheme.TECH_AI

    orchestrator = SFXOrchestrator(
        project_dir=project_dir,
        theme=theme_enum,
        use_library=use_library,
    )

    return orchestrator.generate_sfx_cues(
        use_llm=use_llm,
        dry_run=dry_run,
    )


def analyze_project_scenes(project_dir: Path) -> dict:
    """Analyze scenes in a project without generating cues.

    Args:
        project_dir: Path to project directory

    Returns:
        Analysis preview dict
    """
    orchestrator = SFXOrchestrator(project_dir=project_dir)
    return orchestrator.preview_analysis()
