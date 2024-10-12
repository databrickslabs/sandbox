import unittest
from unittest import skip

from databricks.sdk import WorkspaceClient

from infra.jobs_infra import JobsInfra


class TestJobsInfra(unittest.TestCase):
    def setUp(self):
        self.config = {}
        self.workspace_client = WorkspaceClient()
        self.jobs_infra = JobsInfra(self.config, self.workspace_client)

    @skip("Skipping this test case to avoid creating an actual job. Uncomment this decorator to run the test and create a real job.")
    def test_create_transformation_job(self):
        self.jobs_infra.create_transformation_job()
        self.assertIn("TRANSFORMATION_JOB_ID", self.config)
        self.assertIsNotNone(self.config["TRANSFORMATION_JOB_ID"])


if __name__ == "__main__":
    unittest.main()
