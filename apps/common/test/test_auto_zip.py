import os
from unittest import TestCase

from apps.common.auto_zip import AutoZip

REPO_ROOT = os.path.realpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../.."))


class TestAutoZip(TestCase):
    def test_dict(self):
        path = os.path.join(REPO_ROOT, "apps/common/test/test_archive_1.zip")
        zip = AutoZip(path, ".txt")

        d = zip.as_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(len(d), 3)

        d = zip.as_dict(include_zip_name=True)
        self.assertIsInstance(d, dict)
        self.assertEqual(len(d), 3)
