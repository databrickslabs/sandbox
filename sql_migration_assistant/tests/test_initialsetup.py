import logging
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from databricks.sdk import WorkspaceClient

from utils.initialsetup import SetUpMigrationAssistant

# Configure logging to show debug output
logging.basicConfig(level=logging.INFO)


class TestGetFilesToUpload(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.test_dir, 'folder1'), exist_ok=True)

        with open(os.path.join(self.test_dir, 'folder1', 'file1.txt'), 'w') as f:
            f.write('This is a test file.')
        with open(os.path.join(self.test_dir, 'file2.txt'), 'w') as f:
            f.write('This is another test file.')

        self.expected_files = set([
            'folder1/file1.txt',
            'file2.txt',
        ])

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_get_files_to_upload(self):
        paths = [
            'folder1',
            'file2.txt',
        ]
        result_files = set(SetUpMigrationAssistant.get_files_to_upload(self.test_dir, paths))
        self.assertEqual(self.expected_files, result_files)

    def test_nonexistent_path(self):
        paths = [
            'nonexistent_file.txt',
            'nonexistent_folder',
        ]
        result_files = SetUpMigrationAssistant.get_files_to_upload(self.test_dir, paths)
        self.assertEqual(result_files, [])

    def test_single_file(self):
        paths = [
            'file2.txt',
        ]
        expected_files = set(['file2.txt'])
        result_files = set(SetUpMigrationAssistant.get_files_to_upload(self.test_dir, paths))
        self.assertEqual(expected_files, result_files)


class TestUploadFiles(unittest.TestCase):
    @patch("utils.initialsetup.FileUploader.upload")
    def test_upload_files(self, mock_upload):
        # Mocking FileUploader.upload to verify that files are being uploaded as expected
        assistant = SetUpMigrationAssistant()
        workspace_client = WorkspaceClient()
        path = Path(__file__).parent.parent.resolve()

        # Perform the upload operation and verify file uploads
        assistant.upload_files(workspace_client, str(path))

        upload_target_paths = [
            "utils/runindatabricks.py",
            "utils/configloader.py",
            "utils/run_review_app.py",
            "jobs/bronze_to_silver.py",
            "jobs/call_agents.py",
            "jobs/silver_to_gold.py",
            "jobs/sql2dbx/",
            "app/llm.py",
            "app/similar_code.py",
            "gradio_app.py",
            "run_app_from_databricks_notebook.py",
            "config.yml",
        ]

        files_to_upload = assistant.get_files_to_upload(str(path), upload_target_paths)

        # Output the list of files to upload for debugging
        logging.info("Files to upload: %s", files_to_upload)

        for file in files_to_upload:
            mock_upload.assert_any_call(os.path.join(str(path), file), file)


if __name__ == '__main__':
    unittest.main()
