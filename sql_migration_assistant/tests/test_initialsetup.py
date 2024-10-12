import unittest
import tempfile
import shutil
import os
from utils.initialsetup import SetUpMigrationAssistant

class TestGetFilesToUpload(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.test_dir, 'folder1'), exist_ok=True)

        # Create test files
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

if __name__ == '__main__':
    unittest.main()
