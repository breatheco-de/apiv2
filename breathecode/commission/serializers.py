import logging

from rest_framework import serializers

logger = logging.getLogger(__name__)


class CommissionReportResponseSerializer(serializers.Serializer):
    """Serializer for the commission report response."""

    influencer = serializers.CharField()
    month = serializers.CharField()
    matured_referral_total = serializers.FloatField()
    usage_total = serializers.FloatField()


class AsyncCommissionResponseSerializer(serializers.Serializer):
    """Serializer for async commission processing response."""

    influencer = serializers.CharField()
    month = serializers.CharField()
    scheduled_user_engagements = serializers.IntegerField()
    scheduled_commissions = serializers.BooleanField()
    mode = serializers.CharField()
