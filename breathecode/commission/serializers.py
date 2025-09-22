import logging

from rest_framework import serializers
from breathecode.utils import serpy
from breathecode.authenticate.serializers import AcademySerializer
from breathecode.admissions.serializers import UserSerializer, CohortSerializer
from breathecode.payments.serializers import GetCurrencySmallSerializer, GetInvoiceSmallSerializer

logger = logging.getLogger(__name__)


class CommissionReportResponseSerializer(serializers.Serializer):
    """Serializer for the commission report response."""

    influencer = serializers.CharField()
    month = serializers.CharField()
    matured_referral_total = serializers.FloatField()
    usage_total = serializers.FloatField()
    is_preview = serializers.BooleanField(required=False)
    warning = serializers.CharField(required=False)


class AsyncCommissionResponseSerializer(serializers.Serializer):
    """Serializer for async commission processing response."""

    influencer = serializers.CharField()
    month = serializers.CharField()
    scheduled_user_engagements = serializers.IntegerField()
    scheduled_commissions = serializers.BooleanField()
    mode = serializers.CharField()


class GeekCreatorPaymentSerializer(serpy.Serializer):
    """Serializer for GeekCreatorPayment model."""

    id = serpy.Field()
    influencer = UserSerializer
    month = serpy.MethodField()
    currency = GetCurrencySmallSerializer
    total_amount = serpy.Field()
    status = serpy.Field()
    status_text = serpy.Field()
    payment_date = serpy.MethodField()
    created_at = serpy.MethodField()
    updated_at = serpy.MethodField()
    commission_count = serpy.MethodField()

    def get_month(self, obj):
        return obj.month.strftime("%Y-%m") if obj.month else None

    def get_payment_date(self, obj):
        return obj.payment_date.isoformat() if obj.payment_date else None

    def get_created_at(self, obj):
        return obj.created_at.isoformat()

    def get_updated_at(self, obj):
        return obj.updated_at.isoformat()

    def get_commission_count(self, obj):
        return obj.commissions.count()


class GeekCreatorCommissionSerializer(serpy.Serializer):
    """Serializer for GeekCreatorCommission model."""

    id = serpy.Field()
    influencer = UserSerializer
    cohort = CohortSerializer
    month = serpy.MethodField()
    commission_type = serpy.Field()
    currency = GetCurrencySmallSerializer
    amount_paid = serpy.Field()
    num_users = serpy.Field()
    usage_commission_count = serpy.MethodField()
    referral_commission_count = serpy.MethodField()
    created_at = serpy.MethodField()
    updated_at = serpy.MethodField()

    def get_month(self, obj):
        return obj.month.strftime("%Y-%m") if obj.month else None

    def get_usage_commission_count(self, obj):
        return obj.usage_commissions.count()

    def get_referral_commission_count(self, obj):
        return obj.referral_commissions.count()

    def get_created_at(self, obj):
        return obj.created_at.isoformat()

    def get_updated_at(self, obj):
        return obj.updated_at.isoformat()


class UserUsageCommissionSerializer(serpy.Serializer):
    """Serializer for UserUsageCommission model."""

    id = serpy.Field()
    influencer = UserSerializer
    user = UserSerializer
    cohort = CohortSerializer
    academy = AcademySerializer
    month = serpy.MethodField()
    user_total_points = serpy.Field()
    cohort_points = serpy.Field()
    paid_amount = serpy.Field()
    commission_amount = serpy.Field()
    currency = GetCurrencySmallSerializer
    details = serpy.Field()
    created_at = serpy.MethodField()
    updated_at = serpy.MethodField()

    def get_month(self, obj):
        return obj.month.strftime("%Y-%m") if obj.month else None

    def get_created_at(self, obj):
        return obj.created_at.isoformat()

    def get_updated_at(self, obj):
        return obj.updated_at.isoformat()


class GeekCreatorReferralCommissionSerializer(serpy.Serializer):
    """Serializer for GeekCreatorReferralCommission model."""

    id = serpy.Field()
    geek_creator = UserSerializer
    buyer = UserSerializer
    invoice = GetInvoiceSmallSerializer
    academy = AcademySerializer
    amount = serpy.Field()
    currency = GetCurrencySmallSerializer
    status = serpy.Field()
    available_at = serpy.MethodField()
    is_matured = serpy.Field()
    status_text = serpy.Field()
    created_at = serpy.MethodField()
    updated_at = serpy.MethodField()

    def get_available_at(self, obj):
        return obj.available_at.isoformat() if obj.available_at else None

    def get_created_at(self, obj):
        return obj.created_at.isoformat()

    def get_updated_at(self, obj):
        return obj.updated_at.isoformat()
