from django.urls import path

from .views import BudgetViewSet, ExpenseViewSet

app_name = "budgets"

urlpatterns = [
    path("summary/", BudgetViewSet.as_view({"get": "list"}), name="budget-summary"),
    path("expenses/mine/", ExpenseViewSet.as_view({"get": "list"}), name="my-expenses"),
]
