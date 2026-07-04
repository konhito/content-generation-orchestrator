"""Tests for Three.js integration in the Remotion project."""

import json
from pathlib import Path

import pytest


class TestRemotionPackageJson:
    """Tests for remotion/package.json Three.js dependencies."""

    @pytest.fixture
    def package_json_path(self, project_root: Path) -> Path:
        """Return path to remotion package.json."""
        return project_root / "remotion" / "package.json"

    @pytest.fixture
    def package_json(self, package_json_path: Path) -> dict:
        """Load and return package.json contents."""
        return json.loads(package_json_path.read_text())

    def test_package_json_exists(self, package_json_path: Path):
        """Test that remotion package.json exists."""
        assert package_json_path.exists(), "remotion/package.json should exist"

    def test_has_three_dependency(self, package_json: dict):
        """Test that three.js is in dependencies."""
        deps = package_json.get("dependencies", {})
        assert "three" in deps, "three should be in dependencies"
        assert deps["three"].startswith("^0.170"), f"three version should be ^0.170.x, got {deps['three']}"

    def test_has_react_three_fiber_dependency(self, package_json: dict):
        """Test that @react-three/fiber is in dependencies."""
        deps = package_json.get("dependencies", {})
        assert "@react-three/fiber" in deps, "@react-three/fiber should be in dependencies"

    def test_has_remotion_three_dependency(self, package_json: dict):
        """Test that @remotion/three is in dependencies."""
        deps = package_json.get("dependencies", {})
        assert "@remotion/three" in deps, "@remotion/three should be in dependencies"
        assert "4.0.242" in deps["@remotion/three"], "@remotion/three should match remotion version"

    def test_has_react_three_drei_dependency(self, package_json: dict):
        """Test that @react-three/drei is in dependencies."""
        deps = package_json.get("dependencies", {})
        assert "@react-three/drei" in deps, "@react-three/drei should be in dependencies"

    def test_has_types_three_dev_dependency(self, package_json: dict):
        """Test that @types/three is in devDependencies."""
        dev_deps = package_json.get("devDependencies", {})
        assert "@types/three" in dev_deps, "@types/three should be in devDependencies"


class TestRemotionConfig:
    """Tests for remotion.config.ts GL renderer configuration."""

    @pytest.fixture
    def config_path(self, project_root: Path) -> Path:
        """Return path to remotion.config.ts."""
        return project_root / "remotion" / "remotion.config.ts"

    @pytest.fixture
    def config_content(self, config_path: Path) -> str:
        """Load and return remotion.config.ts contents."""
        return config_path.read_text()

    def test_config_file_exists(self, config_path: Path):
        """Test that remotion.config.ts exists."""
        assert config_path.exists(), "remotion/remotion.config.ts should exist"

    def test_has_chromium_opengl_renderer_setting(self, config_content: str):
        """Test that Config.setChromiumOpenGlRenderer is set."""
        assert "setChromiumOpenGlRenderer" in config_content, (
            "remotion.config.ts should have setChromiumOpenGlRenderer"
        )

    def test_uses_angle_renderer(self, config_content: str):
        """Test that angle renderer is configured."""
        assert '"angle"' in config_content or "'angle'" in config_content, (
            "remotion.config.ts should use 'angle' renderer"
        )


class TestThreeSceneWrapperComponent:
    """Tests for ThreeSceneWrapper component file."""

    @pytest.fixture
    def component_path(self, project_root: Path) -> Path:
        """Return path to ThreeSceneWrapper.tsx."""
        return project_root / "remotion" / "src" / "components" / "three" / "ThreeSceneWrapper.tsx"

    @pytest.fixture
    def component_content(self, component_path: Path) -> str:
        """Load and return ThreeSceneWrapper.tsx contents."""
        return component_path.read_text()

    def test_component_file_exists(self, component_path: Path):
        """Test that ThreeSceneWrapper.tsx exists."""
        assert component_path.exists(), "ThreeSceneWrapper.tsx should exist"

    def test_uses_react_fc_pattern(self, component_content: str):
        """Test that component uses React.FC pattern."""
        assert "React.FC" in component_content, (
            "ThreeSceneWrapper should use React.FC pattern"
        )

    def test_has_props_interface(self, component_content: str):
        """Test that component has a Props interface."""
        assert "ThreeSceneWrapperProps" in component_content, (
            "ThreeSceneWrapper should have ThreeSceneWrapperProps interface"
        )

    def test_exports_component(self, component_content: str):
        """Test that component is exported."""
        assert "export const ThreeSceneWrapper" in component_content, (
            "ThreeSceneWrapper should be exported"
        )

    def test_imports_three_canvas(self, component_content: str):
        """Test that ThreeCanvas is imported from @remotion/three."""
        assert 'from "@remotion/three"' in component_content, (
            "Should import from @remotion/three"
        )
        assert "ThreeCanvas" in component_content, (
            "Should import ThreeCanvas"
        )

    def test_imports_perspective_camera(self, component_content: str):
        """Test that PerspectiveCamera is imported from @react-three/drei."""
        assert 'from "@react-three/drei"' in component_content, (
            "Should import from @react-three/drei"
        )
        assert "PerspectiveCamera" in component_content, (
            "Should import PerspectiveCamera"
        )

    def test_uses_video_config(self, component_content: str):
        """Test that component uses useVideoConfig hook."""
        assert "useVideoConfig" in component_content, (
            "ThreeSceneWrapper should use useVideoConfig hook"
        )

    def test_has_default_lighting(self, component_content: str):
        """Test that component has default lighting setup."""
        assert "ambientLight" in component_content, (
            "ThreeSceneWrapper should have ambient light"
        )
        assert "directionalLight" in component_content, (
            "ThreeSceneWrapper should have directional light"
        )

    def test_has_camera_position_prop(self, component_content: str):
        """Test that component accepts cameraPosition prop."""
        assert "cameraPosition" in component_content, (
            "ThreeSceneWrapper should accept cameraPosition prop"
        )

    def test_has_camera_fov_prop(self, component_content: str):
        """Test that component accepts cameraFov prop."""
        assert "cameraFov" in component_content, (
            "ThreeSceneWrapper should accept cameraFov prop"
        )


class TestThreeComponentExports:
    """Tests for three component exports (index.ts)."""

    @pytest.fixture
    def index_path(self, project_root: Path) -> Path:
        """Return path to three/index.ts."""
        return project_root / "remotion" / "src" / "components" / "three" / "index.ts"

    @pytest.fixture
    def index_content(self, index_path: Path) -> str:
        """Load and return index.ts contents."""
        return index_path.read_text()

    def test_index_file_exists(self, index_path: Path):
        """Test that index.ts exists."""
        assert index_path.exists(), "three/index.ts should exist"

    def test_exports_three_scene_wrapper(self, index_content: str):
        """Test that ThreeSceneWrapper is exported."""
        assert "ThreeSceneWrapper" in index_content, (
            "index.ts should export ThreeSceneWrapper"
        )

    def test_exports_props_type(self, index_content: str):
        """Test that ThreeSceneWrapperProps type is exported."""
        assert "ThreeSceneWrapperProps" in index_content, (
            "index.ts should export ThreeSceneWrapperProps type"
        )


class TestThreeDirectoryStructure:
    """Tests for three component directory structure."""

    def test_three_directory_exists(self, project_root: Path):
        """Test that three components directory exists."""
        three_dir = project_root / "remotion" / "src" / "components" / "three"
        assert three_dir.exists(), "components/three directory should exist"
        assert three_dir.is_dir(), "components/three should be a directory"

    def test_has_expected_files(self, project_root: Path):
        """Test that all expected files exist in three directory."""
        three_dir = project_root / "remotion" / "src" / "components" / "three"
        expected_files = ["index.ts", "ThreeSceneWrapper.tsx", "ThreeSceneWrapper.test.tsx"]

        for file_name in expected_files:
            file_path = three_dir / file_name
            assert file_path.exists(), f"{file_name} should exist in three directory"
