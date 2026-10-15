from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from routing.views import route_map

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="map", query_string=True)),
    path("admin/", admin.site.urls),
    path("api/", include("routing.urls")),
    path("map/", route_map, name="map"),
]
