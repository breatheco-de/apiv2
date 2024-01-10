# Signals and receivers

A signal is a way to decouple the logic inside the [models](./models.md), a signal is like an Airtag, when an Airtag becomes closer to another device it should trigger an action, your action is wrapped inside a receiver and the signal is the emitter, this signal should be trigger manually in the cases of a custom signal or automatically in case of the signals which was created by Django like `pre_save` which is execute before executing `model.save()`.

## Writing signals

Read [this](https://docs.djangoproject.com/en/5.0/topics/signals/#defining-signals).

## Writing receivers

Read [this](https://docs.djangoproject.com/en/5.0/topics/signals/).

## Setting up the app to enable the signals

Read [this](https://docs.djangoproject.com/en/5.0/topics/signals/#django.dispatch.receiver).

## Django signals

read [this](https://docs.djangoproject.com/en/5.0/ref/signals/).

## Where are the signals

It where in `breathecode/APP_NAME/signals.py`.

## Where are the receivers

It where in `breathecode/APP_NAME/receivers.py`.

## Where are tested the signals?

It where in `breathecode/APP_NAME/tests/signals/tests_SIGNAL_NAME.py`.

## Where are tested the receivers?

It where in `breathecode/APP_NAME/tests/receivers/tests_RECEIVER_NAME.py`.
