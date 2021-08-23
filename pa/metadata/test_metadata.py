from unittest import TestCase

from django.urls import reverse

from fin.serializers.utils import PrimaryKeyRelatedField
from metadata.metadata import Metadata


class MetadataTestCases(TestCase):
    def test_metadata(self):
        """
        Tests that metadata contains url field
        """
        test_view_name = 'sources-list'
        test_field = PrimaryKeyRelatedField(queryset=[], view_name=test_view_name)

        metadata = Metadata()
        json_metadata = metadata.get_field_info(test_field)

        self.assertEqual(reverse(test_view_name), json_metadata['url'])
