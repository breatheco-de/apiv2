from breathecode.admissions.models import Academy


def foos(request):
    context = {}
    academy_id = None
    if 'Academy' in request.headers:
        academy_id = request.headers['Academy']
    elif 'academy' in request.headers:
        academy_id = request.headers['academy']

    if academy_id is not None:
        context['academy'] = Academy.objects.get(academy_id)

    return context
