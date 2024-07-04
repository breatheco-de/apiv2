import random
from unittest.mock import MagicMock, call, patch

from breathecode.payments import signals
from breathecode.tests.mixins.legacy import LegacyAPITestCase


class TestSignal(LegacyAPITestCase):

    @patch("breathecode.payments.signals.lose_service_permissions.send_robust", MagicMock())
    def test__consumable_how_many_minus_1__consume_gte_1(self, enable_signals):
        enable_signals()

        how_many_consume = random.randint(1, 100)
        how_many = -1
        consumable = {"how_many": how_many}
        model = self.bc.database.create(consumable=consumable)
        consumable_db = self.bc.format.to_dict(model.consumable)

        signals.consume_service.send(
            sender=model.consumable.__class__, instance=model.consumable, how_many=how_many_consume
        )

        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            [
                {
                    **consumable_db,
                    "how_many": how_many,
                },
            ],
        )
        self.assertEqual(signals.lose_service_permissions.send_robust.call_args_list, [])

    @patch("breathecode.payments.signals.lose_service_permissions.send_robust", MagicMock())
    def test__consumable_how_many_0__consume_gte_1(self, enable_signals):
        enable_signals()

        how_many_consume = random.randint(1, 100)
        how_many = 0
        consumable = {"how_many": how_many}
        model = self.bc.database.create(consumable=consumable)
        consumable_db = self.bc.format.to_dict(model.consumable)

        signals.consume_service.send(
            sender=model.consumable.__class__, instance=model.consumable, how_many=how_many_consume
        )

        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            [
                {
                    **consumable_db,
                    "how_many": how_many,
                },
            ],
        )
        self.assertEqual(
            signals.lose_service_permissions.send_robust.call_args_list,
            [
                call(sender=model.consumable.__class__, instance=model.consumable),
            ],
        )

    @patch("breathecode.payments.signals.lose_service_permissions.send_robust", MagicMock())
    def test__consumable_how_many_gte_1__consume_gte_1(self, enable_signals):
        enable_signals()

        how_many_consume = random.randint(1, 100)
        how_many = random.randint(1, 100)
        consumable = {"how_many": how_many + how_many_consume}
        model = self.bc.database.create(consumable=consumable)
        consumable_db = self.bc.format.to_dict(model.consumable)

        signals.consume_service.send(
            sender=model.consumable.__class__, instance=model.consumable, how_many=how_many_consume
        )

        self.assertEqual(
            self.bc.database.list_of("payments.Consumable"),
            [
                {
                    **consumable_db,
                    "how_many": how_many,
                },
            ],
        )
        self.assertEqual(signals.lose_service_permissions.send_robust.call_args_list, [])
