import uuid

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.models.category import Category
from api.models.company import Company


class CategoryViewTests(APITestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Test Company")
        self.other_company = Company.objects.create(name="Other Company")
        self.root_category = Category.objects.create(
            company=self.company,
            name="Root Category",
        )

    def test_list(self):
        url = reverse("category-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_retrieve(self):
        url = reverse("category-detail", args=[self.root_category.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Root Category")
        self.assertEqual(str(response.data["id"]), str(self.root_category.id))
        self.assertEqual(str(response.data["company"]), str(self.company.id))
        self.assertIsNone(response.data["parent_category"])
        self.assertIn("created_at", response.data)
        self.assertIn("updated_at", response.data)

    def test_retrieve_not_found(self):
        url = reverse("category-detail", args=[uuid.uuid4()])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create(self):
        url = reverse("category-list")
        data = {"company": str(self.company.id), "name": "New Root Category"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Category.objects.count(), 2)
        self.assertEqual(response.data["name"], "New Root Category")
        self.assertNotIn("parent_category", response.data)

    def test_create_does_not_accept_parent_category(self):
        """ルートカテゴリ作成時に parent_category を渡しても無視される"""
        url = reverse("category-list")
        data = {
            "company": str(self.company.id),
            "name": "Should Be Root",
            "parent_category": str(self.root_category.id),
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_id = response.data["id"]
        created = Category.objects.get(id=created_id)
        self.assertIsNone(created.parent_category)

    def test_create_duplicate_name_same_company(self):
        url = reverse("category-list")
        data = {"company": str(self.company.id), "name": "Root Category"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_same_name_different_company(self):
        url = reverse("category-list")
        data = {"company": str(self.other_company.id), "name": "Root Category"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_missing_name(self):
        url = reverse("category-list")
        data = {"company": str(self.company.id)}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_missing_company(self):
        url = reverse("category-list")
        data = {"name": "No Company"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_child(self):
        url = reverse("category-children", args=[self.root_category.id])
        data = {"company": str(self.company.id), "name": "Child Category"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            str(response.data["parent_category"]), str(self.root_category.id)
        )

    def test_create_child_parent_not_found(self):
        url = reverse("category-children", args=[uuid.uuid4()])
        data = {"company": str(self.company.id), "name": "Child Category"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_child_company_mismatch(self):
        """子カテゴリの company が親カテゴリの company と異なる場合はエラー"""
        url = reverse("category-children", args=[self.root_category.id])
        data = {"company": str(self.other_company.id), "name": "Mismatch Child"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_child_missing_name(self):
        url = reverse("category-children", args=[self.root_category.id])
        data = {"company": str(self.company.id)}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_child_missing_company(self):
        url = reverse("category-children", args=[self.root_category.id])
        data = {"name": "No Company Child"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_blank_name(self):
        url = reverse("category-list")
        data = {"company": str(self.company.id), "name": "   "}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_child_blank_name(self):
        url = reverse("category-children", args=[self.root_category.id])
        data = {"company": str(self.company.id), "name": "   "}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update(self):
        url = reverse("category-detail", args=[self.root_category.id])
        data = {
            "company": str(self.company.id),
            "name": "Updated Category",
            "parent_category": None,
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.root_category.refresh_from_db()
        self.assertEqual(self.root_category.name, "Updated Category")

    def test_update_not_found(self):
        url = reverse("category-detail", args=[uuid.uuid4()])
        data = {
            "company": str(self.company.id),
            "name": "Updated Category",
            "parent_category": None,
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_partial_update(self):
        url = reverse("category-detail", args=[self.root_category.id])
        response = self.client.patch(url, {"name": "Patched Category"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.root_category.refresh_from_db()
        self.assertEqual(self.root_category.name, "Patched Category")

    def test_partial_update_not_found(self):
        url = reverse("category-detail", args=[uuid.uuid4()])
        response = self.client.patch(url, {"name": "Patched Category"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_blank_name(self):
        url = reverse("category-detail", args=[self.root_category.id])
        data = {"company": str(self.company.id), "name": "   ", "parent_category": None}
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_self_as_parent(self):
        """自身を親カテゴリに設定できないこと"""
        url = reverse("category-detail", args=[self.root_category.id])
        data = {
            "company": str(self.company.id),
            "name": "Root Category",
            "parent_category": str(self.root_category.id),
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_circular_parent(self):
        """循環参照となる親カテゴリを設定できないこと"""
        child = Category.objects.create(
            company=self.company,
            name="Child",
            parent_category=self.root_category,
        )
        url = reverse("category-detail", args=[self.root_category.id])
        data = {
            "company": str(self.company.id),
            "name": "Root Category",
            "parent_category": str(child.id),
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_parent_different_company(self):
        """別企業の親カテゴリを設定できないこと"""
        other_root = Category.objects.create(
            company=self.other_company, name="Other Root"
        )
        url = reverse("category-detail", args=[self.root_category.id])
        data = {
            "company": str(self.company.id),
            "name": "Root Category",
            "parent_category": str(other_root.id),
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_partial_update_company_with_existing_parent_different_company(self):
        """PATCH で company を変更した場合、既存 parent_category との企業不一致を検出すること"""
        child = Category.objects.create(
            company=self.company,
            name="Child",
            parent_category=self.root_category,
        )
        url = reverse("category-detail", args=[child.id])
        response = self.client.patch(
            url, {"company": str(self.other_company.id)}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_partial_update_self_as_parent(self):
        """PATCH でも自身を親カテゴリに設定できないこと"""
        url = reverse("category-detail", args=[self.root_category.id])
        response = self.client.patch(
            url, {"parent_category": str(self.root_category.id)}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_partial_update_circular_parent(self):
        """PATCH でも循環参照となる親カテゴリを設定できないこと"""
        child = Category.objects.create(
            company=self.company,
            name="Child",
            parent_category=self.root_category,
        )
        url = reverse("category-detail", args=[self.root_category.id])
        response = self.client.patch(
            url, {"parent_category": str(child.id)}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_destroy(self):
        url = reverse("category-detail", args=[self.root_category.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(id=self.root_category.id).exists())

    def test_destroy_sets_child_parent_to_null(self):
        """親カテゴリ削除時に子の parent_category が NULL になること（SET_NULL）"""
        child = Category.objects.create(
            company=self.company,
            name="Child",
            parent_category=self.root_category,
        )
        url = reverse("category-detail", args=[self.root_category.id])
        self.client.delete(url)
        child.refresh_from_db()
        self.assertIsNone(child.parent_category)

    def test_destroy_not_found(self):
        url = reverse("category-detail", args=[uuid.uuid4()])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
