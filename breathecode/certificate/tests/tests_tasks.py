# """
# Tasks tests
# """
# from django.test import TestCase
# from ..tasks import add

# class AddTestCase(TestCase):

#     def testNoError(self):
#         """Test that the ``add`` task runs with no errors,
#         and returns the correct result."""
#         result = add.delay(8, 8)

#         self.assertEqual(result.get(), 16)
#         self.assertTrue(result.successful())
