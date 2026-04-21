# 動作確認手順

## 前提

```shell
### マイグレーション
PIPENV_IGNORE_VIRTUALENVS=1 pipenv run python manage.py migrate

### サーバー起動
PIPENV_IGNORE_VIRTUALENVS=1 pipenv run python manage.py runserver
```

Company は API がないため Django shell で作成する。

```shell
### 例：Docker で起動している場合
docker compose exec db psql -U root -d coding-test -c "SELECT id, name FROM companies;"
 id | name
----+------
(0 rows)
```

```shell
export COMPANY_ID=$(PIPENV_IGNORE_VIRTUALENVS=1 pipenv run python manage.py shell -c "
from api.models.company import Company
c, _ = Company.objects.get_or_create(name='Test Company')
print(c.id)
" 2>/dev/null | tail -1)
echo $COMPANY_ID

export OTHER_COMPANY_ID=$(PIPENV_IGNORE_VIRTUALENVS=1 pipenv run python manage.py shell -c "
from api.models.company import Company
c, _ = Company.objects.get_or_create(name='Other Company')
print(c.id)
" 2>/dev/null | tail -1)
echo $OTHER_COMPANY_ID
```

## API コール

### 一覧取得

```shell
curl -s http://localhost:8000/api/categories/ | jq
[]
```

### ルートカテゴリ作成

```shell
export ROOT_ID=$(curl -s -X POST http://localhost:8000/api/categories/ \
  -H "Content-Type: application/json" \
  -d "{\"company\": \"$COMPANY_ID\", \"name\": \"食品\"}" \
  | jq -r '.id')
echo $ROOT_ID
6dd568cc-10e1-40b4-a7be-a26772b48fdb
```

### 子カテゴリ作成

```shell
export CHILD_ID=$(curl -s -X POST http://localhost:8000/api/categories/$ROOT_ID/children/ \
  -H "Content-Type: application/json" \
  -d "{\"company\": \"$COMPANY_ID\", \"name\": \"野菜\"}" \
  | jq -r '.id')
echo $CHILD_ID
dcde3958-2acc-470a-a70e-51887ce5d4db
```

### 詳細取得

```shell
curl -s http://localhost:8000/api/categories/$ROOT_ID/ | jq
```

- レスポンスの例

```json
{
  "id": "6dd568cc-10e1-40b4-a7be-a26772b48fdb",
  "company": "91608c8f-9668-4923-b922-6a83832140a9",
  "name": "食品",
  "parent_category": null,
  "created_at": "2026-04-21T20:22:38.187967Z",
  "updated_at": "2026-04-21T20:22:38.187977Z"
}
```

### 全フィールド更新（PUT）

```shell
curl -s -X PUT http://localhost:8000/api/categories/$ROOT_ID/ \
  -H "Content-Type: application/json" \
  -d "{\"company\": \"$COMPANY_ID\", \"name\": \"食品・飲料\", \"parent_category\": null}" | jq
```

- レスポンスの例

```json
{
  "id": "6dd568cc-10e1-40b4-a7be-a26772b48fdb",
  "company": "91608c8f-9668-4923-b922-6a83832140a9",
  "name": "食品・飲料",
  "parent_category": null,
  "created_at": "2026-04-21T20:22:38.187967Z",
  "updated_at": "2026-04-21T20:24:44.587519Z"
}
```

### 部分更新（PATCH）

```shell
curl -s -X PATCH http://localhost:8000/api/categories/$ROOT_ID/ \
  -H "Content-Type: application/json" \
  -d '{"name": "食品・飲料・菓子"}' | jq
```

- レスポンスの例

```json
{
  "id": "6dd568cc-10e1-40b4-a7be-a26772b48fdb",
  "company": "91608c8f-9668-4923-b922-6a83832140a9",
  "name": "食品・飲料・菓子",
  "parent_category": null,
  "created_at": "2026-04-21T20:22:38.187967Z",
  "updated_at": "2026-04-21T20:25:36.516672Z"
}
```

### 削除

```shell
curl -s -o /dev/null -w "HTTP %{http_code}\n" -X DELETE http://localhost:8000/api/categories/$CHILD_ID/
HTTP 204
```

## バリデーションエラー確認

### 準備：別企業のルートカテゴリを作成

```shell
export OTHER_ROOT_ID=$(curl -s -X POST http://localhost:8000/api/categories/ \
  -H "Content-Type: application/json" \
  -d "{\"company\": \"$OTHER_COMPANY_ID\", \"name\": \"電化製品\"}" \
  | jq -r '.id')
```

### 1. 同企業・同名の重複

```shell
curl -s -X POST http://localhost:8000/api/categories/ \
  -H "Content-Type: application/json" \
  -d "{\"company\": \"$COMPANY_ID\", \"name\": \"食品・飲料・菓子\"}" | jq
```

- エラー例 ：`"POST /api/categories/ HTTP/1.1" 400 73`

```json
{ "non_field_errors": ["The fields company, name must make a unique set."] }
```

### 2. 空白のみ name

```shell
curl -s -X POST http://localhost:8000/api/categories/ \
  -H "Content-Type: application/json" \
  -d "{\"company\": \"$COMPANY_ID\", \"name\": \"   \"}" | jq
```

- エラー例 ：`"POST /api/categories/ HTTP/1.1" 400 70`

```json
{ "name": ["カテゴリ名に空白のみは使用できません。"] }
```

### 3. children で別企業の company

```shell
curl -s -X POST http://localhost:8000/api/categories/$OTHER_ROOT_ID/children/ \
  -H "Content-Type: application/json" \
  -d "{\"company\": \"$COMPANY_ID\", \"name\": \"不正な子\"}" | jq
```

- エラー例 ：`"POST /api/categories/{id}/children/ HTTP/1.1" 400 96`

```json
{ "parent_category": ["親カテゴリは同一企業に属している必要があります。"] }
```

### 4. 自己参照

```shell
curl -s -X PATCH http://localhost:8000/api/categories/$ROOT_ID/ \
  -H "Content-Type: application/json" \
  -d "{\"parent_category\": \"$ROOT_ID\"}" | jq
```

- エラー例 ：`"PATCH /api/categories/{id}/ HTTP/1.1" 400 102`

```json
{ "parent_category": ["カテゴリ自身を親カテゴリに設定することはできません。"] }
```

### 5. 循環参照

※ 子カテゴリが存在する状態で実行（削除済みの場合は先に再作成しておくこと）

```shell
### 子カテゴリがない場合は再作成
export CHILD_ID=$(curl -s -X POST http://localhost:8000/api/categories/$ROOT_ID/children/ \
  -H "Content-Type: application/json" \
  -d "{\"company\": \"$COMPANY_ID\", \"name\": \"野菜\"}" | jq -r '.id')

curl -s -X PATCH http://localhost:8000/api/categories/$ROOT_ID/ \
  -H "Content-Type: application/json" \
  -d "{\"parent_category\": \"$CHILD_ID\"}" | jq
```

- エラー例 ：`"PATCH /api/categories/{id}/ HTTP/1.1" 400 87`

```json
{ "parent_category": ["循環参照となる親カテゴリは設定できません。"] }
```

### 6. PUT で別企業の parent_category

```shell
curl -s -X PUT http://localhost:8000/api/categories/$ROOT_ID/ \
  -H "Content-Type: application/json" \
  -d "{\"company\": \"$COMPANY_ID\", \"name\": \"食品・飲料・菓子\", \"parent_category\": \"$OTHER_ROOT_ID\"}" | jq
```

- エラー例 ：`"PUT /api/categories/{id}/ HTTP/1.1" 400 96`

```json
{ "parent_category": ["親カテゴリは同一企業に属している必要があります。"] }
```

### 7. 存在しない ID

```shell
curl -s http://localhost:8000/api/categories/00000000-0000-0000-0000-000000000000/ | jq
```

- エラー例 ：`"GET /api/categories/00000000-0000-0000-0000-000000000000/ HTTP/1.1" 404 49`

```json
{ "detail": "No Category matches the given query." }
```

## テスト実行

```shell
### 全テスト
PIPENV_IGNORE_VIRTUALENVS=1 pipenv run python manage.py test api.tests

### 詳細表示
PIPENV_IGNORE_VIRTUALENVS=1 pipenv run python manage.py test api.tests --verbosity=2

### 関数単位
pipenv run python manage.py test api.tests.test_views.CategoryViewTests.test_create
```
