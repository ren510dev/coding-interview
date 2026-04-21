from rest_framework import serializers

from api.models.category import Category

BLANK_NAME_ERROR = "カテゴリ名に空白のみは使用できません。"


def validate_name_not_blank(value):
    if not value.strip():
        raise serializers.ValidationError(BLANK_NAME_ERROR)
    return value


class RootCategorySerializer(serializers.ModelSerializer):
    """ルートカテゴリ（親なし）作成用シリアライザ"""

    name = serializers.CharField(max_length=255, trim_whitespace=False)

    class Meta:
        model = Category
        fields = ["id", "company", "name", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        return validate_name_not_blank(value)


class ChildCategorySerializer(serializers.ModelSerializer):
    """子カテゴリ（親あり）作成用シリアライザ"""

    name = serializers.CharField(max_length=255, trim_whitespace=False)

    class Meta:
        model = Category
        fields = [
            "id",
            "company",
            "name",
            "parent_category",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "parent_category", "created_at", "updated_at"]

    def validate_name(self, value):
        return validate_name_not_blank(value)

    def validate(self, attrs):
        parent = self.context.get("parent_category")
        company = attrs.get("company")
        if (
            parent is not None
            and company is not None
            and parent.company_id != company.pk
        ):
            raise serializers.ValidationError(
                {"parent_category": "親カテゴリは同一企業に属している必要があります。"}
            )
        return attrs


class CategorySerializer(serializers.ModelSerializer):
    """一覧・詳細取得・更新用シリアライザ"""

    name = serializers.CharField(max_length=255, trim_whitespace=False)

    class Meta:
        model = Category
        fields = [
            "id",
            "company",
            "name",
            "parent_category",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        return validate_name_not_blank(value)

    def validate(self, attrs):
        if "parent_category" in attrs:
            parent = attrs["parent_category"]
        elif self.instance is not None:
            parent = self.instance.parent_category
        else:
            parent = None

        company = attrs.get("company") or (
            self.instance.company if self.instance else None
        )

        if parent is not None and company is not None:
            self._validate_parent_company(parent, company)
            self._validate_no_cycle(parent)

        return attrs

    def _validate_parent_company(self, parent, company):
        if parent.company_id != company.pk:
            raise serializers.ValidationError(
                {"parent_category": "親カテゴリは同一企業に属している必要があります。"}
            )

    def _validate_no_cycle(self, parent):
        instance = self.instance
        if instance is None:
            return
        if parent.pk == instance.pk:
            raise serializers.ValidationError(
                {
                    "parent_category": "カテゴリ自身を親カテゴリに設定することはできません。"
                }
            )
        ancestor = parent
        while ancestor.parent_category_id is not None:
            if ancestor.parent_category_id == instance.pk:
                raise serializers.ValidationError(
                    {"parent_category": "循環参照となる親カテゴリは設定できません。"}
                )
            ancestor = ancestor.parent_category
