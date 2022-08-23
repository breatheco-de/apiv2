# Using mocks

## Mock object

Mock objects are simulated objects that mimic the behavior of real objects in controlled ways, most often as part of a software testing initiative. A programmer typically creates a mock object to test the behavior of some other object, in much the same way that a car designer uses a crash test dummy to simulate the dynamic behavior of a human in vehicle impacts.

## How to apply a automatic mock

### `The most easier way to create a mock`

The decorator `@patch.object` is the best option to implement a mock

```python
@patch.object(object_class_or_module, 'method_or_function_to_be_mocked', MagicMock())
```

### `This is the code to test`

```python
# utils.py
from .actions import shoot_gun, kenny_s_birth, show

def kenny_killer(kenny_id: int) -> None:
    # get the current kenny
    kenny = Kenny.objects.filter(id=kenny_id).first()

    # see - South Park - Coon and friends
    if kenny:
        shoot_gun(kenny)
        kenny_number = kenny_s_birth()
        show(kenny_number)
```

### `This is a example of use of mocks`

```python
from unittest.mock import MagicMock, call, patch
from rest_framework.test import APITestCase
from .models import Kenny
from .utils import kenny_killer

import app.actions as actions

# this is a wrapper that implement the kenny_s_birth static behavior to the test
def kenny_s_birth_mock(number: int):
    def kenny_s_birth():
        return number

    # the side_effect is a function that manage the behavior of the mocked function
    return MagicMock(side_effect=kenny_s_birth)

class KennyTestSuite(APITestCase):
    # 🔽 this function is automatically mocked
    @patch.object(actions, 'shoot_gun', MagicMock())

    # 🔽 this function is manually mocked
    @patch.object(actions, 'kenny_s_birth', kenny_s_birth_mock(1000))

    # 🔽 this function is automatically mocked
    @patch.object(actions, 'show', MagicMock())

    def test_kill_kenny(self):
        kenny = Kenny()
        kenny.save()

        kenny_killer(kenny_id=1)

        # shoot_gun() is called with a kenny instance
        self.assertEqual(actions.shoot_gun.call_args_list, [call(kenny)])

        # kenny_s_birth() is called with zero arguments
        self.assertEqual(actions.kenny_s_birth.call_args_list, [call()])

        # show is called
        self.assertEqual(actions.show.call_args_list, [call(1)])
```
