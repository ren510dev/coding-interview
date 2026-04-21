from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.models.category import Category
from api.serializers.category import CategorySerializer, ChildCategorySerializer, RootCategorySerializer


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.select_related("company", "parent_category").all()
    serializer_class = CategorySerializer

    def get_serializer_class(self):
        if self.action == "create":
            return RootCategorySerializer
        return CategorySerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == "children":
            context["parent_category"] = self.get_object()
        return context

    @action(detail=True, methods=["post"], url_path="children")
    def children(self, request, pk=None):
        parent = self.get_object()
        serializer = ChildCategorySerializer(
            data=request.data,
            context={"request": request, "parent_category": parent},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(parent_category=parent)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
