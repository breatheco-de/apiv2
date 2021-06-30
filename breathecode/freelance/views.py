from django.shortcuts import render
from rest_framework.response import Response
from .serializers import BillSerializer, SmallIssueSerializer, BigBillSerializer
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from .actions import sync_user_issues, generate_freelancer_bill
from .models import Bill, Freelancer, Issue
from rest_framework.views import APIView
from breathecode.notify.actions import get_template_content
from django.http import HttpResponse


@api_view(['GET'])
@permission_classes([AllowAny])
def render_html_bill(request, id=None):
    item = Bill.objects.filter(id=id).first()
    if item is None:
        template = get_template_content("message",
                                        {"message": "Bill not found"})
        return HttpResponse(template['html'])
    else:
        serializer = BigBillSerializer(item, many=False)
        data = {
            **serializer.data, "issues":
            SmallIssueSerializer(item.issue_set.all(), many=True).data
        }
        template = get_template_content("invoice", data)
        return HttpResponse(template['html'])


# Create your views here.
class BillView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    def get(self, request, format=None):

        items = Bill.objects.all()
        lookup = {}

        if 'freelancer' in self.request.GET:
            userId = self.request.GET.get('freelancer')
            lookup['freelancer__id'] = userId

        if 'user' in self.request.GET:
            userId = self.request.GET.get('user')
            lookup['freelancer__user__id'] = userId

        if 'status' in self.request.GET:
            status = self.request.GET.get('status')
            lookup['status'] = status

        items = items.filter(**lookup).order_by('-created_at')

        serializer = BillSerializer(items, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = BillSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SingleBillView(APIView):
    """
    List all snippets, or create a new snippet.
    """
    def get(self, request, id):
        item = Bill.objects.filter(id=id).first()
        if item is None:
            raise serializers.ValidationError("Bill not found", code=404)
        else:
            serializer = BillSerializer(item, many=False)
            return Response(serializer.data)

    def put(self, request, id=None):
        item = Bill.objects.filter(id=id).first()
        if item is None:
            raise serializers.ValidationError("Bill not found", code=404)

        serializer = BillSerializer(item, data=request.data, many=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Create your views here.
@api_view(['GET'])
def sync_user_issues(request):
    tags = sync_user_issues()
    return Response(tags, status=status.HTTP_200_OK)


# Create your views here.
@api_view(['GET'])
def get_issues(request):
    issues = Issue.objects.all()

    lookup = {}

    if 'freelancer' in request.GET:
        userId = request.GET.get('freelancer')
        lookup['freelancer__id'] = userId

    if 'bill' in request.GET:
        _id = request.GET.get('bill')
        lookup['bill__id'] = _id

    if 'status' in request.GET:
        _status = request.GET.get('status')
        lookup['status'] = _status.upper()

    issues = issues.filter(**lookup).order_by('-created_at')

    serializer = SmallIssueSerializer(issues, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# Create your views here.
@api_view(['GET'])
def get_latest_bill(request, user_id=None):
    freelancer = Freelancer.objects.filter(user__id=user_id).first()

    if freelancer is None or reviewer is None:
        raise serializers.ValidationError("Freelancer or reviewer not found",
                                          code=404)

    open_bill = generate_freelancer_bill(freelancer)
    return Response(open_bill, status=status.HTTP_200_OK)
