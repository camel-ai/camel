from unittest import TestCase

import apps.data_explorer.loader as loader


class TestLoader(TestCase):
    def test_load_datasets_smoke(self):
        data = loader.load_datasets()
        self.assertIsNotNone(data)
