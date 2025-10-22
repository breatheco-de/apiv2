#!/usr/bin/env python
"""
Test script to verify AcademyService ForeignKey change works correctly.
This tests that multiple academies can have AcademyServices for the same service.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_settings")
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from breathecode.payments.models import Service, AcademyService, Currency
from breathecode.admissions.models import Academy


def test_multiple_academies_same_service():
    """Test that multiple academies can price the same service."""
    print("Testing AcademyService ForeignKey relationship...")
    
    # Clean up any existing test data
    Service.objects.filter(slug="test-service").delete()
    Academy.objects.filter(slug__in=["test-academy-1", "test-academy-2"]).delete()
    
    # Create test service
    service = Service.objects.create(
        slug="test-service",
        title="Test Service",
        type="VOID"
    )
    print(f"✓ Created service: {service.slug}")
    
    # Create test academies
    academy1 = Academy.objects.create(
        slug="test-academy-1",
        name="Test Academy 1"
    )
    academy2 = Academy.objects.create(
        slug="test-academy-2",
        name="Test Academy 2"
    )
    print(f"✓ Created academies: {academy1.slug}, {academy2.slug}")
    
    # Create currency
    currency, _ = Currency.objects.get_or_create(
        code="USD",
        defaults={"name": "US Dollar"}
    )
    print(f"✓ Using currency: {currency.code}")
    
    # Test 1: Create AcademyService for academy1
    try:
        academy_service1 = AcademyService.objects.create(
            academy=academy1,
            service=service,
            currency=currency,
            price_per_unit=100.0
        )
        print(f"✓ Test 1 PASSED: Created AcademyService for {academy1.slug}")
    except Exception as e:
        print(f"✗ Test 1 FAILED: Could not create AcademyService for {academy1.slug}: {e}")
        return False
    
    # Test 2: Create AcademyService for academy2 with the SAME service
    # This should work with ForeignKey but would fail with OneToOneField
    try:
        academy_service2 = AcademyService.objects.create(
            academy=academy2,
            service=service,
            currency=currency,
            price_per_unit=150.0
        )
        print(f"✓ Test 2 PASSED: Created AcademyService for {academy2.slug} with same service")
    except Exception as e:
        print(f"✗ Test 2 FAILED: Could not create second AcademyService: {e}")
        return False
    
    # Test 3: Verify both AcademyServices exist
    count = AcademyService.objects.filter(service=service).count()
    if count == 2:
        print(f"✓ Test 3 PASSED: Found {count} AcademyServices for the same service")
    else:
        print(f"✗ Test 3 FAILED: Expected 2 AcademyServices, found {count}")
        return False
    
    # Test 4: Verify unique_together constraint
    # Attempt to create duplicate (same academy + same service)
    try:
        AcademyService.objects.create(
            academy=academy1,
            service=service,
            currency=currency,
            price_per_unit=200.0
        )
        print(f"✗ Test 4 FAILED: Should not allow duplicate academy+service")
        return False
    except Exception as e:
        print(f"✓ Test 4 PASSED: Correctly prevented duplicate academy+service: {type(e).__name__}")
    
    # Test 5: Verify filtering works correctly
    academy1_services = AcademyService.objects.filter(academy=academy1, service=service)
    academy2_services = AcademyService.objects.filter(academy=academy2, service=service)
    
    if academy1_services.count() == 1 and academy2_services.count() == 1:
        print(f"✓ Test 5 PASSED: Filtering by academy+service works correctly")
    else:
        print(f"✗ Test 5 FAILED: Filtering issue (academy1: {academy1_services.count()}, academy2: {academy2_services.count()})")
        return False
    
    # Cleanup
    service.delete()
    academy1.delete()
    academy2.delete()
    print("\n✓ Cleanup complete")
    
    print("\n" + "="*60)
    print("ALL TESTS PASSED! ✓")
    print("="*60)
    print("\nThe ForeignKey change works correctly:")
    print("- Multiple academies can price the same service")
    print("- unique_together constraint prevents duplicates")
    print("- Filtering by academy+service works as expected")
    return True


if __name__ == "__main__":
    success = test_multiple_academies_same_service()
    sys.exit(0 if success else 1)

