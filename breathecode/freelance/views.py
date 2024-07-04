from datetime import datetime

from django.db.models import Q
from django.http import HttpResponse
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from breathecode.notify.actions import get_template_content
from breathecode.utils.api_view_extensions.api_view_extensions import APIViewExtensions
from breathecode.utils.decorators import capable_of
from breathecode.utils.views import private_view
from capyc.rest_framework.exceptions import ValidationException

from .actions import generate_freelancer_bill, generate_project_invoice
from .models import (
    BILL_STATUS,
    AcademyFreelanceProject,
    Bill,
    FreelanceProjectMember,
    Freelancer,
    Issue,
    ProjectInvoice,
)
from .serializers import (
    BigBillSerializer,
    BigInvoiceSerializer,
    BigProjectSerializer,
    BillSerializer,
    SmallBillSerializer,
    SmallFreelancerMemberSerializer,
    SmallIssueSerializer,
)


@private_view()
def render_html_all_bills(request, token):

    def map_status(_status):
        status_maper = {
            "DUE": "under review",
            "APPROVED": "ready to pay",
            "PAID": "already paid",
            "IGNORED": "ignored",
        }
        if _status not in status_maper:
            return _status
        return status_maper[_status]

    lookup = {}

    status = "APPROVED"
    if "status" in request.GET:
        status = request.GET.get("status")
    lookup["status"] = status.upper()

    if "academy" in request.GET:
        lookup["academy__id__in"] = request.GET.get("academy").split(",")

    items = Bill.objects.filter(**lookup).exclude(academy__isnull=True)
    serializer = BigBillSerializer(items, many=True)

    total_price = 0
    for bill in serializer.data:
        total_price += bill["total_price"]

    data = {
        "status": status,
        "token": token.key,
        "title": f"Payments {map_status(status)}",
        "possible_status": [(key, map_status(key)) for key, label in BILL_STATUS],
        "bills": serializer.data,
        "total_price": total_price,
    }
    template = get_template_content("bills", data)
    return HttpResponse(template["html"])


@api_view(["GET"])
@permission_classes([AllowAny])
def render_html_bill(request, id=None):
    item = Bill.objects.filter(id=id).first()
    if item is None:
        template = get_template_content("message", {"message": "Bill not found"})
        return HttpResponse(template["html"])
    else:
        serializer = BigBillSerializer(item, many=False)
        status_map = {"DUE": "UNDER_REVIEW", "APPROVED": "READY_TO_PAY", "PAID": "ALREADY PAID"}

        data = {
            **serializer.data,
            "issues": SmallIssueSerializer(item.issue_set.all(), many=True).data,
            "status": status_map[serializer.data["status"]],
            "title": f'Freelancer { serializer.data["freelancer"]["user"]["first_name"] } '
            f'{ serializer.data["freelancer"]["user"]["last_name"] } - Invoice { item.id }',
        }
        template = get_template_content("invoice", data, academy=item.academy)
        return HttpResponse(template["html"])


# Create your views here.
class BillView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    def get(self, request, format=None):

        items = Bill.objects.all()
        lookup = {}

        if "freelancer" in self.request.GET:
            user_id = self.request.GET.get("freelancer")
            lookup["freelancer__id"] = user_id

        if "user" in self.request.GET:
            user_id = self.request.GET.get("user")
            lookup["freelancer__user__id"] = user_id

        if "status" in self.request.GET:
            status = self.request.GET.get("status")
            lookup["status"] = status

        items = items.filter(**lookup).order_by("-created_at")

        serializer = BillSerializer(items, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = BillSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AcademyBillView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    extensions = APIViewExtensions(sort="-created_at", paginate=True)

    @capable_of("read_freelancer_bill")
    def get(self, request, academy_id, bill_id=None):

        def get_freelancer_by_name_or_email(query_name, query):
            for term in query_name.split():
                query = query.filter(
                    Q(freelancer__user__first_name__icontains=term)
                    | Q(freelancer__user__last_name__icontains=term)
                    | Q(freelancer__user__email__icontains=term)
                )
            return query

        if bill_id is not None:
            item = Bill.objects.filter(id=id).first()
            if item is None:
                raise serializers.ValidationError("Bill not found", code=404)
            else:
                serializer = BillSerializer(item, many=False)
                return Response(serializer.data)

        handler = self.extensions(request)
        items = Bill.objects.filter(academy__id=academy_id)
        lookup = {}

        like = request.GET.get("like", None)
        if like is not None:
            items = get_freelancer_by_name_or_email(like, items)

        freelancer = self.request.GET.get("freelancer", None)
        if freelancer is not None:
            lookup["freelancer__id"] = freelancer.id

        status = self.request.GET.get("status", "")
        if status != "":
            lookup["status__in"] = status.split(",")

        user_id = self.request.GET.get("user", None)
        if user_id is not None:
            lookup["freelancer__user__id"] = user_id

        reviewer = self.request.GET.get("reviewer", None)
        if reviewer is not None:
            lookup["reviewer__id"] = reviewer.id

        sort = self.request.GET.get("sort", "-created_at")
        items = items.filter(**lookup).order_by(sort)

        items = handler.queryset(items)
        serializer = SmallBillSerializer(items, many=True)
        return handler.response(serializer.data)

    @capable_of("crud_freelancer_bill")
    def put(self, request, bill_id=None, academy_id=None):
        # Bulk Action to Modify Status
        if bill_id is None:
            bill_status = request.data["status"]
            bills = request.data["bills"]

            if bill_status is None or bill_status == "":
                raise ValidationException("Status not found in the body of the request", code=404)

            if bill_status not in ["DUE", "APPROVED", "PAID", "IGNORED"]:
                raise ValidationException(f"Status provided ({bill_status}) is not a valid status", code=404)

            if bills is None or len(bills) == 0:
                raise ValidationException("Bills not found in the body of the request", code=404)

            for bill in bills:
                item = Bill.objects.filter(id=bill, academy__id=academy_id).first()
                if item is None:
                    raise ValidationException("Bill not found for this academy", code=404)
                item.status = bill_status
                item.save()
                bill = item

            return Response(f"Bills' status successfully updated to {bill_status}", status=status.HTTP_201_CREATED)

        item = Bill.objects.filter(id=bill_id, academy__id=academy_id).first()
        if item is None:
            raise ValidationException("Bill not found for this academy", code=404)

        serializer = BillSerializer(item, data=request.data, many=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AcademyProjectView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    @capable_of("read_freelance_projects")
    def get(self, request, academy_id, project_id=None):

        if project_id is not None:
            item = AcademyFreelanceProject.objects.filter(id=project_id, academy__id=academy_id).first()
            if item is None:
                raise ValidationException("Project not found on this academy", 404)
            serializer = BigProjectSerializer(item, many=False)
            return Response(serializer.data)

        items = AcademyFreelanceProject.objects.filter(academy__id=academy_id)
        lookup = {}

        if "like" in self.request.GET:
            like = self.request.GET.get("like")
            lookup["title__icontains"] = like

        if "repository" in self.request.GET:
            repository = self.request.GET.get("repository")
            lookup["repository__icontains"] = repository

        items = items.filter(**lookup).order_by("-title")

        serializer = BigProjectSerializer(items, many=True)
        return Response(serializer.data)


class AcademyProjectMemberView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    @capable_of("read_freelance_projects")
    def get(self, request, academy_id):

        items = FreelanceProjectMember.objects.filter(project__academy__id=academy_id)
        lookup = {}

        def find_user_by_name(query_name, qs):
            for term in query_name.split():
                qs = qs.filter(Q(first_name__icontains=term) | Q(last_name__icontains=term))
            return qs

        if "like" in self.request.GET:
            like = self.request.GET.get("like")
            if "@" in like:
                items = items.filter(Q(freelancer__user__email__icontains=like))
            else:
                for term in like.split():
                    items = items.filter(
                        Q(freelancer__user__first_name__icontains=term) | Q(freelancer__user__last_name__icontains=term)
                    )

        if "project" in self.request.GET:
            project = self.request.GET.get("project")
            lookup["project__id"] = project

        items = items.filter(**lookup).order_by("-freelancer__user__first_name")

        serializer = SmallFreelancerMemberSerializer(items, many=True)
        return Response(serializer.data)


class AcademyInvoiceMemberView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    permission_classes = [AllowAny]

    def get(self, request, invoice_id):

        invoice = ProjectInvoice.objects.filter(id=invoice_id).first()
        if invoice is None:
            raise ValidationException(f"No invoice with id {invoice_id}", slug="invoice-not-found")

        items = FreelanceProjectMember.objects.filter(project__id=invoice.project.id)
        lookup = {}

        def find_user_by_name(query_name, qs):
            for term in query_name.split():
                qs = qs.filter(Q(first_name__icontains=term) | Q(last_name__icontains=term))
            return qs

        if "like" in self.request.GET:
            like = self.request.GET.get("like")
            if "@" in like:
                items = items.filter(Q(freelancer__user__email__icontains=like))
            else:
                for term in like.split():
                    items = items.filter(
                        Q(freelancer__user__first_name__icontains=term) | Q(freelancer__user__last_name__icontains=term)
                    )

        if "project" in self.request.GET:
            project = self.request.GET.get("project")
            lookup["project__id"] = project

        items = items.filter(**lookup).order_by("-freelancer__user__first_name")

        serializer = SmallFreelancerMemberSerializer(items, many=True)
        return Response(serializer.data)


class AcademyProjectInvoiceView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    @capable_of("read_project_invoice")
    def get(self, request, invoice_id=None, academy_id=None, project_id=None):

        if invoice_id is not None:
            item = ProjectInvoice.objects.filter(project__academy__id=academy_id, id=invoice_id).first()
            if item is None:
                raise ValidationException("Project Invoice user not found", 404)
            serializer = BigInvoiceSerializer(item, many=False)
            return Response(serializer.data)

        items = ProjectInvoice.objects.filter(project__academy__id=academy_id)
        lookup = {}

        if "like" in self.request.GET:
            like = self.request.GET.get("like")
            lookup["project__title__icontains"] = like

        project = self.request.GET.get("project", project_id)
        if project:
            lookup["project__id"] = project

        if "status" in self.request.GET:
            status = self.request.GET.get("status")
            lookup["status__iexact"] = status

        if "after" in self.request.GET:
            after = self.request.GET.get("after")
            after = datetime.strptime(after, "%Y-%m-%d").date()
            items = items.filter(created_at__gte=after)
        if "before" in self.request.GET:
            before = self.request.GET.get("before")
            before = datetime.strptime(before, "%Y-%m-%d").date()
            items = items.filter(created_at__lte=before)

        items = items.filter(**lookup).order_by("-created_at")

        serializer = BillSerializer(items, many=True)
        return Response(serializer.data)

    @capable_of("crud_project_invoice")
    def post(self, request, academy_id=None, project_id=None):

        if project_id is None:
            raise ValidationException("Missing project ID on the URL", code=404, slug="argument-not-provided")

        project = AcademyFreelanceProject.objects.filter(id=project_id, academy__id=academy_id).first()
        if project is None:
            raise ValidationException("This project does not exist for this academy", code=404, slug="not-found")

        invoices = generate_project_invoice(project)
        serializer = BigInvoiceSerializer(invoices, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SingleInvoiceView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    permission_classes = [AllowAny]

    def get(self, request, id):
        item = ProjectInvoice.objects.filter(id=id).first()
        if item is None:
            raise ValidationException("Invoice not found", slug="invoice-not-found", code=404)
        else:
            serializer = BigInvoiceSerializer(item, many=False)
            return Response(serializer.data)


class SingleBillView(APIView):
    """
    List all snippets, or create a new snippet.
    """

    def get(self, request, id):
        item = Bill.objects.filter(id=id).first()
        if item is None:
            raise serializers.ValidationError("Bill not found", code=404)
        else:
            serializer = BigBillSerializer(item, many=False)
            return Response(serializer.data)

    @capable_of("crud_freelancer_bill")
    def put(self, request, id=None, academy_id=None):
        item = Bill.objects.filter(id=id, academy__id=academy_id).first()
        if item is None:
            raise serializers.ValidationError("Bill not found for this academy", code=404)

        serializer = BillSerializer(item, data=request.data, many=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Create your views here.
@api_view(["GET"])
def sync_user_issues(request):
    from .actions import sync_user_issues

    tags = sync_user_issues()
    return Response(tags, status=status.HTTP_200_OK)


# Create your views here.
@api_view(["GET"])
def get_issues(request):
    issues = Issue.objects.all()

    lookup = {}

    if "freelancer" in request.GET:
        user_id = request.GET.get("freelancer")
        lookup["freelancer__id"] = user_id

    if "bill" in request.GET:
        _id = request.GET.get("bill")
        lookup["bill__id"] = _id

    if "status" in request.GET:
        _status = request.GET.get("status")
        lookup["status"] = _status.upper()

    issues = issues.filter(**lookup).order_by("-created_at")

    serializer = SmallIssueSerializer(issues, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# Create your views here.
@api_view(["GET"])
def get_latest_bill(request, user_id=None):
    freelancer = Freelancer.objects.filter(user__id=user_id).first()
    reviewer = None

    if freelancer is None:
        reviewer = Bill.objects.filter(reviewer__id=user_id).first()

    if freelancer is None or reviewer is None:
        raise serializers.ValidationError("Freelancer or reviewer not found", code=404)

    open_bills = generate_freelancer_bill(freelancer or reviewer.freelancer)
    return Response(open_bills, status=status.HTTP_200_OK)
