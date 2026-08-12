from django.db import connection, reset_queries
from django.http import JsonResponse

from .models import LSAProfile


def n_plus_one_test(request):
    reset_queries()

    lsas = LSAProfile.objects.filter(is_active=True)

    results = []

    for lsa in lsas:
        skills = list(lsa.skills.all())

        results.append({
            "name": lsa.name,
            "skills": [skill.name for skill in skills],
        })

    query_count_without_prefetch = len(connection.queries)

    reset_queries()

    lsas = (
        LSAProfile.objects
        .filter(is_active=True)
        .prefetch_related("skills")
    )

    results_optimized = []

    for lsa in lsas:
        skills = list(lsa.skills.all())

        results_optimized.append({
            "name": lsa.name,
            "skills": [skill.name for skill in skills],
        })

    query_count_with_prefetch = len(connection.queries)

    return JsonResponse({
        "without_prefetch": {
            "query_count": query_count_without_prefetch,
            "results": results,
        },
        "with_prefetch": {
            "query_count": query_count_with_prefetch,
            "results": results_optimized,
        },
    })