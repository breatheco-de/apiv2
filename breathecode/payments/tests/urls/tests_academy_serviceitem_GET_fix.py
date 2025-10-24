# Temporary file to generate fixed test code
# This will be deleted after use

tests_to_fix = [
    ("renew_at", [("renew_at", [1, 3]), ("how_many", [10, 20])], "renew_at=3", "renew_at", 3),
    (
        "renew_at_unit",
        [("renew_at_unit", ["MONTH", "WEEK"]), ("how_many", [10, 20])],
        "renew_at_unit=week",
        "renew_at_unit",
        "WEEK",
    ),
    ("how_many", [("how_many", [10, 20, -1])], "how_many=-1", "how_many", -1),
    ("how_many_gt", [("how_many", [5, 15, 25])], "how_many_gt=10", None, None),
    ("how_many_lt", [("how_many", [5, 15, 25])], "how_many_lt=20", None, None),
    (
        "unit_type",
        [("unit_type", ["UNIT", "CREDIT"]), ("how_many", [10, 20])],
        "unit_type=credit",
        "unit_type",
        "CREDIT",
    ),
    (
        "multiple_unit_types",
        [("unit_type", ["UNIT", "CREDIT", "LICENSE"]), ("how_many", [10, 20, 30])],
        "unit_type=unit,credit",
        None,
        None,
    ),
]


# Helper function to generate test method
def generate_test(name, attrs_list, query, assert_field, assert_value):
    test_items = len(attrs_list[0][1])

    # Create service_item setup code
    setup_code = []
    for i in range(test_items):
        item_setup = [f"        model.service_item[{i}].service = model.service"]
        for attr_name, values in attrs_list:
            if isinstance(values[i], str):
                item_setup.append(f'        model.service_item[{i}].{attr_name} = "{values[i]}"')
            else:
                item_setup.append(f"        model.service_item[{i}].{attr_name} = {values[i]}")
        item_setup.append(f"        model.service_item[{i}].save()")
        setup_code.append("\n".join(item_setup))

    test_code = f'''    def test_get__filter_by_{name}(self):
        """Test filtering by {name}"""
        model = self.bc.database.create(
            user=1,
            role=1,
            capability="read_service",
            profile_academy=1,
            service=1,
            service_item={test_items},
        )

        model.service.owner = model.academy
        model.service.save()

{chr(10).join(setup_code)}

        self.bc.request.authenticate(model.user)

        url = "/v1/payments/academy/serviceitem?{query}"
        response = self.client.get(url, headers={{"academy": 1}})

        json = response.json()

        self.assertEqual(response.status_code, 200)'''

    if assert_field:
        test_code += f'''
        self.assertEqual(len(json), 1)
        self.assertEqual(json[0]["{assert_field}"], {"\"" + assert_value + "\"" if isinstance(assert_value, str) else assert_value})'''
    else:
        # Custom assertions for special cases
        if "gt" in name:
            test_code += """
        self.assertEqual(len(json), 2)
        self.assertTrue(all(item["how_many"] > 10 for item in json))"""
        elif "lt" in name:
            test_code += """
        self.assertEqual(len(json), 2)
        self.assertTrue(all(item["how_many"] < 20 for item in json))"""
        elif "multiple" in name:
            test_code += """
        self.assertEqual(len(json), 2)
        unit_types = [item["unit_type"] for item in json]
        self.assertIn("UNIT", unit_types)
        self.assertIn("CREDIT", unit_types)"""

    return test_code


# Generate all tests
for test_data in tests_to_fix:
    print(generate_test(*test_data))
    print()
