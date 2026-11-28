from django.urls import path

from comicsdb.views.maintenance import MaintenanceCheckList, MaintenanceOverview

app_name = "maintenance"
urlpatterns = [
    path("", MaintenanceOverview.as_view(), name="overview"),
    path("<slug:check>/", MaintenanceCheckList.as_view(), name="check"),
]
