"""Kiểm quy tắc nhóm tên nguồn và tránh rò nhiều lát cắt một YouTube ID."""
import unittest
from scripts.inventory_temporal_sources import group
from scripts.inspect_temporal_pilot import source_is_development_eligible


class InventoryTests(unittest.TestCase):
    def test_multiple_numeric_suffixes_share_source(self):
        self.assertEqual(group('pA6q7Q2EQrw_25_00'), 'pA6q7Q2EQrw')
        self.assertEqual(group('pA6q7Q2EQrw_0_00'), 'pA6q7Q2EQrw')
        self.assertEqual(group('-FQxK6HdxNU_00'), '-FQxK6HdxNU')

    def test_source_test_is_not_development(self):
        self.assertFalse(source_is_development_eligible({'split_in_distribution': 'test', 'split_geo_aware': 'train'}))
        self.assertTrue(source_is_development_eligible({'split_in_distribution': 'train', 'split_geo_aware': 'train'}))


if __name__ == '__main__':
    unittest.main()
