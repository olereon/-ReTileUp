"""Unit tests for batch renaming tool."""

import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from retileup.tools.batch_renamer import BatchRenamerTool, BatchRenamerConfig
from retileup.core.exceptions import ProcessingError, ValidationError


class TestBatchRenamerConfig:
    """Test BatchRenamerConfig validation and functionality."""

    def test_valid_config(self, tmp_path):
        """Test creation of valid configuration."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"
        processed_file = tmp_path / "processed.txt"

        input_dir.mkdir()

        config = BatchRenamerConfig(
            input_path=input_dir,
            output_dir=output_dir,
            processed_file=processed_file,
            naming_pattern="{date}_{index:09d}",
            date_format="%Y-%m-%d"
        )

        assert config.input_path == input_dir
        assert config.output_dir == output_dir
        assert config.processed_file == processed_file
        assert config.naming_pattern == "{date}_{index:09d}"
        assert config.date_format == "%Y-%m-%d"
        assert config.use_current_date is True
        assert config.preserve_original_extension is True
        assert config.delete_originals is False

    def test_invalid_naming_pattern(self, tmp_path):
        """Test validation of naming pattern."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"

        # Missing {date} placeholder
        with pytest.raises(ValueError, match="must contain \\{date\\}"):
            BatchRenamerConfig(
                input_path=input_dir,
                output_dir=output_dir,
                naming_pattern="{index:09d}"
            )

        # Missing {index} placeholder
        with pytest.raises(ValueError, match="must contain \\{index"):
            BatchRenamerConfig(
                input_path=input_dir,
                output_dir=output_dir,
                naming_pattern="{date}_file"
            )

    def test_invalid_date_format(self, tmp_path):
        """Test validation of date format."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"

        with pytest.raises(ValueError, match="Invalid date format"):
            BatchRenamerConfig(
                input_path=input_dir,
                output_dir=output_dir,
                date_format="%Z"  # Invalid format code
            )

    def test_extensions_normalization(self, tmp_path):
        """Test file extensions are normalized properly."""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "output"

        config = BatchRenamerConfig(
            input_path=input_dir,
            output_dir=output_dir,
            supported_extensions={"jpg", ".PNG", ".TIFF"}
        )

        expected = {".jpg", ".png", ".tiff"}
        assert config.supported_extensions == expected


class TestBatchRenamerTool:
    """Test BatchRenamerTool functionality."""

    @pytest.fixture
    def tool(self):
        """Create a BatchRenamerTool instance."""
        return BatchRenamerTool()

    @pytest.fixture
    def sample_images(self, tmp_path):
        """Create sample image files for testing."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create sample images
        image_files = []
        for i, name in enumerate(["image1.jpg", "photo_2.png", "scan.tiff"]):
            image_path = input_dir / name
            # Create a simple test image
            img = Image.new('RGB', (100, 100), color=(255, 0, 0))
            img.save(image_path)
            image_files.append(image_path)

        return input_dir, image_files

    def test_tool_properties(self, tool):
        """Test tool basic properties."""
        assert tool.name == "batch-rename"
        assert "rename" in tool.description.lower()
        assert tool.version == "1.0.0"
        assert tool.get_config_schema() == BatchRenamerConfig

    def test_validate_config_missing_input(self, tool, tmp_path):
        """Test validation with missing input directory."""
        config = BatchRenamerConfig(
            input_path=tmp_path / "nonexistent",
            output_dir=tmp_path / "output"
        )

        errors = tool.validate_config(config)
        assert len(errors) == 1
        assert "not found" in errors[0]

    def test_validate_config_input_not_directory(self, tool, tmp_path):
        """Test validation when input path is not a directory."""
        # Create a file instead of directory
        input_file = tmp_path / "input.txt"
        input_file.write_text("test")

        config = BatchRenamerConfig(
            input_path=input_file,
            output_dir=tmp_path / "output"
        )

        errors = tool.validate_config(config)
        assert len(errors) == 1
        assert "not a directory" in errors[0]

    def test_validate_config_no_image_files(self, tool, tmp_path):
        """Test validation when no image files are found."""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        # Create non-image file
        (input_dir / "document.txt").write_text("test")

        config = BatchRenamerConfig(
            input_path=input_dir,
            output_dir=tmp_path / "output"
        )

        errors = tool.validate_config(config)
        assert len(errors) == 1
        assert "No supported image files" in errors[0]

    def test_validate_config_same_input_output(self, tool, tmp_path):
        """Test validation when input and output are the same."""
        input_dir = tmp_path / "images"
        input_dir.mkdir()

        config = BatchRenamerConfig(
            input_path=input_dir,
            output_dir=input_dir
        )

        errors = tool.validate_config(config)
        assert any("cannot be the same" in error for error in errors)

    def test_validate_config_success(self, tool, sample_images):
        """Test successful validation."""
        input_dir, _ = sample_images
        output_dir = input_dir.parent / "output"

        config = BatchRenamerConfig(
            input_path=input_dir,
            output_dir=output_dir
        )

        errors = tool.validate_config(config)
        assert len(errors) == 0

    def test_find_image_files(self, tool, sample_images):
        """Test finding image files in directory."""
        input_dir, expected_files = sample_images

        supported_extensions = {'.jpg', '.png', '.tiff'}
        found_files = tool._find_image_files(input_dir, supported_extensions)

        assert len(found_files) == 3
        found_names = {f.name for f in found_files}
        expected_names = {f.name for f in expected_files}
        assert found_names == expected_names

    def test_load_processed_file_empty(self, tool, tmp_path):
        """Test loading empty processed file."""
        config = BatchRenamerConfig(
            input_path=tmp_path / "input",
            output_dir=tmp_path / "output",
            processed_file=tmp_path / "processed.txt"
        )

        tool._load_processed_file(config)
        assert tool._processed_entries == []

    def test_load_processed_file_with_entries(self, tool, tmp_path):
        """Test loading processed file with existing entries."""
        processed_file = tmp_path / "processed.txt"
        processed_file.write_text("2024-01-15_000000001.jpg\n2024-01-15_000000002.png\n")

        config = BatchRenamerConfig(
            input_path=tmp_path / "input",
            output_dir=tmp_path / "output",
            processed_file=processed_file
        )

        tool._load_processed_file(config)
        assert len(tool._processed_entries) == 2
        assert "2024-01-15_000000001.jpg" in tool._processed_entries
        assert "2024-01-15_000000002.png" in tool._processed_entries

    def test_get_current_date(self, tool, tmp_path):
        """Test getting current date."""
        config = BatchRenamerConfig(
            input_path=tmp_path / "input",
            output_dir=tmp_path / "output",
            use_current_date=True,
            date_format="%Y-%m-%d"
        )

        current_date = tool._get_current_date(config)
        expected_date = datetime.now().strftime("%Y-%m-%d")
        assert current_date == expected_date

    def test_get_next_index_empty(self, tool):
        """Test getting next index with empty processed entries."""
        tool._processed_entries = []
        next_index = tool._get_next_index("2024-01-15")
        assert next_index == 1

    def test_get_next_index_with_entries(self, tool):
        """Test getting next index with existing entries."""
        tool._processed_entries = [
            "2024-01-15_000000001.jpg",
            "2024-01-15_000000002.png",
            "2024-01-14_000000001.jpg"
        ]

        next_index = tool._get_next_index("2024-01-15")
        assert next_index == 3

    def test_generate_filename(self, tool, tmp_path):
        """Test filename generation."""
        original_file = tmp_path / "image.jpg"

        config = BatchRenamerConfig(
            input_path=tmp_path / "input",
            output_dir=tmp_path / "output",
            naming_pattern="{date}_{index:09d}",
            preserve_original_extension=True
        )

        filename = tool._generate_filename(config, "2024-01-15", 1, original_file)
        assert filename == "2024-01-15_000000001.jpg"

    def test_generate_filename_no_preserve_extension(self, tool, tmp_path):
        """Test filename generation without preserving extension."""
        original_file = tmp_path / "image.tiff"

        config = BatchRenamerConfig(
            input_path=tmp_path / "input",
            output_dir=tmp_path / "output",
            naming_pattern="{date}_{index:09d}",
            preserve_original_extension=False
        )

        filename = tool._generate_filename(config, "2024-01-15", 1, original_file)
        assert filename == "2024-01-15_000000001.jpg"

    def test_execute_dry_run(self, tool, sample_images):
        """Test dry run execution."""
        input_dir, _ = sample_images
        output_dir = input_dir.parent / "output"

        config = BatchRenamerConfig(
            input_path=input_dir,
            output_dir=output_dir,
            dry_run=True
        )

        result = tool.execute(config)

        assert result.success is True
        assert "3 files" in result.message
        assert len(result.output_files) == 3
        assert not output_dir.exists()  # No actual files created
        assert result.metadata["dry_run"] is True

    def test_execute_success(self, tool, sample_images):
        """Test successful execution."""
        input_dir, original_files = sample_images
        output_dir = input_dir.parent / "output"
        processed_file = input_dir.parent / "processed.txt"

        config = BatchRenamerConfig(
            input_path=input_dir,
            output_dir=output_dir,
            processed_file=processed_file,
            verbose=True
        )

        result = tool.execute(config)

        assert result.success is True
        assert "3 files" in result.message
        assert len(result.output_files) == 3
        assert output_dir.exists()

        # Check that files were created
        output_files = list(output_dir.glob("*.jpg")) + list(output_dir.glob("*.png")) + list(output_dir.glob("*.tiff"))
        assert len(output_files) == 3

        # Check processed file was updated
        assert processed_file.exists()
        processed_content = processed_file.read_text()
        assert "000000001" in processed_content
        assert "000000002" in processed_content
        assert "000000003" in processed_content

        # Original files should still exist
        for original_file in original_files:
            assert original_file.exists()

    def test_execute_with_delete_originals(self, tool, sample_images):
        """Test execution with delete originals option."""
        input_dir, original_files = sample_images
        output_dir = input_dir.parent / "output"

        config = BatchRenamerConfig(
            input_path=input_dir,
            output_dir=output_dir,
            delete_originals=True
        )

        result = tool.execute(config)

        assert result.success is True
        assert len(result.output_files) == 3
        assert result.metadata["deleted_originals"] is True

        # Original files should be deleted
        for original_file in original_files:
            assert not original_file.exists()

    def test_execute_force_overwrite(self, tool, sample_images):
        """Test execution with force overwrite."""
        input_dir, _ = sample_images
        output_dir = input_dir.parent / "output"
        output_dir.mkdir()

        # Create existing file
        existing_file = output_dir / "2024-01-15_000000001.jpg"
        existing_file.write_text("existing")

        config = BatchRenamerConfig(
            input_path=input_dir,
            output_dir=output_dir,
            force_overwrite=True
        )

        result = tool.execute(config)

        assert result.success is True
        assert len(result.output_files) == 3

    def test_execute_no_force_overwrite_fails(self, sample_images):
        """Test execution fails without force overwrite when files exist."""
        from datetime import datetime

        # Create a fresh tool instance to avoid state pollution
        tool = BatchRenamerTool()

        input_dir, _ = sample_images
        output_dir = input_dir.parent / "output"
        processed_file = input_dir.parent / "test_processed.txt"
        output_dir.mkdir()

        # Create empty processed file to start with index 1
        processed_file.touch()

        # Get current date to match what tool will use
        current_date = datetime.now().strftime("%Y-%m-%d")

        # Create existing file that will conflict with first file (index 1)
        # Based on alphabetical sorting, first file should be image1.jpg -> .jpg extension
        existing_file = output_dir / f"{current_date}_000000001.jpg"
        existing_file.write_text("existing")

        config = BatchRenamerConfig(
            input_path=input_dir,
            output_dir=output_dir,
            processed_file=processed_file,
            force_overwrite=False
        )

        result = tool.execute(config)

        # Should partially succeed (other files processed)
        assert result.success is False
        assert result.metadata["files_failed"] > 0
        assert "Output file exists" in str(result.metadata["failed_files"][0]["error"])

    def test_execute_invalid_config_type(self, tool):
        """Test execution with invalid config type."""
        from retileup.tools.base import ToolConfig

        invalid_config = ToolConfig(input_path=Path("/tmp"))
        result = tool.execute(invalid_config)

        assert result.success is False
        assert "Invalid config type" in result.message
        assert result.error_code == "INVALID_CONFIG"

    def test_extract_date_from_filename(self, tool):
        """Test extracting date from filename."""
        # Test successful extraction
        date = tool._extract_date_from_filename("2024-01-15_000000001.jpg", "%Y-%m-%d")
        assert date == "2024-01-15"

        # Test failed extraction
        date = tool._extract_date_from_filename("invalid_filename.jpg", "%Y-%m-%d")
        assert date is None

    def test_add_processed_entry(self, tool, tmp_path):
        """Test adding entry to processed file."""
        processed_file = tmp_path / "processed.txt"

        tool._add_processed_entry("test_filename.jpg", processed_file)

        assert processed_file.exists()
        content = processed_file.read_text()
        assert "test_filename.jpg" in content
        assert "test_filename.jpg" in tool._processed_entries

    def test_setup_and_cleanup(self, tool):
        """Test tool setup and cleanup."""
        # Test initial state
        assert tool._processed_entries == []
        assert tool._last_index == 0
        assert tool._current_date == ""

        # Setup
        tool.setup()
        assert tool._setup_called is True

        # Set some state
        tool._processed_entries = ["test"]
        tool._last_index = 5
        tool._current_date = "2024-01-15"

        # Cleanup
        tool.cleanup()
        assert tool._cleanup_called is True
        assert tool._processed_entries == []
        assert tool._last_index == 0
        assert tool._current_date == ""

    @pytest.mark.parametrize("extensions,expected_count", [
        ({".jpg", ".png", ".tiff"}, 3),
        ({".jpg"}, 1),
        ({".png"}, 1),
        ({".bmp"}, 0),  # Not present
    ])
    def test_find_files_by_extension(self, tool, sample_images, extensions, expected_count):
        """Test finding files by specific extensions."""
        input_dir, _ = sample_images

        found_files = tool._find_image_files(input_dir, extensions)
        assert len(found_files) == expected_count

    def test_execute_with_custom_date_format(self, tool, sample_images):
        """Test execution with custom date format."""
        input_dir, _ = sample_images
        output_dir = input_dir.parent / "output"

        config = BatchRenamerConfig(
            input_path=input_dir,
            output_dir=output_dir,
            date_format="%Y%m%d",
            naming_pattern="{date}_{index:06d}"
        )

        result = tool.execute(config)

        assert result.success is True
        assert len(result.output_files) == 3

        # Check filename format
        output_files = list(output_dir.glob("*"))
        for output_file in output_files:
            assert len(output_file.stem.split('_')[0]) == 8  # YYYYMMDD format
            assert len(output_file.stem.split('_')[1]) == 6   # 6-digit index


@pytest.mark.integration
class TestBatchRenamerIntegration:
    """Integration tests for batch renaming tool."""

    def test_full_workflow(self, tmp_path):
        """Test complete batch renaming workflow."""
        # Setup directories and files
        input_dir = tmp_path / "photos"
        output_dir = tmp_path / "renamed"
        processed_file = tmp_path / "processed.txt"

        input_dir.mkdir()

        # Create test images
        image_files = []
        for i, name in enumerate(["IMG_001.jpg", "IMG_002.png", "scan_document.tiff"]):
            image_path = input_dir / name
            img = Image.new('RGB', (200, 150), color=(i*50, i*70, i*90))
            img.save(image_path)
            image_files.append(image_path)

        # Create tool and config
        tool = BatchRenamerTool()
        config = BatchRenamerConfig(
            input_path=input_dir,
            output_dir=output_dir,
            processed_file=processed_file,
            naming_pattern="{date}_{index:09d}",
            date_format="%Y-%m-%d",
            preserve_original_extension=True,
            delete_originals=False,
            verbose=True
        )

        # Validate configuration
        errors = tool.validate_config(config)
        assert len(errors) == 0

        # Execute renaming
        result = tool.execute_with_timing(config)

        # Verify results
        assert result.success is True
        assert len(result.output_files) == 3
        assert result.execution_time is not None
        assert result.execution_time > 0

        # Check output files exist and have correct names
        output_files = sorted(output_dir.glob("*"))
        assert len(output_files) == 3

        for i, output_file in enumerate(output_files, 1):
            # Check filename pattern
            assert f"_{i:09d}" in output_file.name

            # Check file is readable image
            img = Image.open(output_file)
            assert img.size == (200, 150)
            img.close()

        # Check processed file
        assert processed_file.exists()
        processed_lines = processed_file.read_text().strip().split('\n')
        assert len(processed_lines) == 3

        # Verify original files still exist (delete_originals=False)
        for original_file in image_files:
            assert original_file.exists()

        # Check metadata
        metadata = result.metadata
        assert metadata["files_renamed"] == 3
        assert metadata["files_failed"] == 0
        assert metadata["dry_run"] is False
        assert metadata["deleted_originals"] is False

    def test_incremental_processing(self, tmp_path):
        """Test processing files in multiple batches."""
        input_dir = tmp_path / "photos"
        output_dir = tmp_path / "renamed"
        processed_file = tmp_path / "processed.txt"

        input_dir.mkdir()

        tool = BatchRenamerTool()

        # First batch
        for name in ["photo1.jpg", "photo2.jpg"]:
            image_path = input_dir / name
            img = Image.new('RGB', (100, 100), color=(255, 0, 0))
            img.save(image_path)

        config = BatchRenamerConfig(
            input_path=input_dir,
            output_dir=output_dir,
            processed_file=processed_file,
            delete_originals=True
        )

        result1 = tool.execute(config)
        assert result1.success is True
        assert len(result1.output_files) == 2

        # Second batch
        for name in ["photo3.jpg", "photo4.jpg"]:
            image_path = input_dir / name
            img = Image.new('RGB', (100, 100), color=(0, 255, 0))
            img.save(image_path)

        result2 = tool.execute(config)
        assert result2.success is True
        assert len(result2.output_files) == 2

        # Check that indexing continued correctly
        all_output_files = sorted(output_dir.glob("*"))
        assert len(all_output_files) == 4

        # Verify index sequence
        for i, output_file in enumerate(all_output_files, 1):
            assert f"_{i:09d}" in output_file.name

        # Check processed file has all entries
        processed_lines = processed_file.read_text().strip().split('\n')
        assert len(processed_lines) == 4