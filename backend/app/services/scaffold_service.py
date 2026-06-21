from pathlib import Path
from ..config import PROJECTS_DIR


SAMPLE_YAML = """- teststeps:
    - step: Getting a resource
      request:
        method: GET
        url: /posts/1
      validate:
        equal:
          - [ "status_code", 200 ]
- teststeps:
    - step: Creating a resource
      request:
        method: POST
        url: /posts
        headers:
          Content-Type: application/json; charset=UTF-8
        json:
          title: 'foo'
          body: 'bar'
          userId: 1
      validate:
        equal:
          - [ "status_code", 201 ]
          - [ "body.userId", 1 ]
          - [ "body.title", "foo" ]
          - [ "body.body", "bar" ]
"""

CONFIG_YAML = """# base URL
base_url: https://jsonplaceholder.typicode.com

test_project:
  sample: True

global_test_config:
  foo: bar
"""

TEST_API_PY = """# test_api.py
from typing import Dict

from lounger.analyze_cases import load_teststeps
from lounger.case import execute_teststeps


@load_teststeps()
def test_api(teststeps: Dict) -> None:
    execute_teststeps(teststeps)
"""

TEST_DIR_CONFTEST_PY = """import pytest

from api.clients.posts_api import PostsAPI
from lounger.utils.config_utils import ConfigUtils


@pytest.fixture(scope="session")
def env_config() -> dict:
    config = ConfigUtils("config/config.yaml")
    return {
        "base_url": config.get_config("base_url"),
    }


@pytest.fixture()
def posts_api(env_config: dict) -> PostsAPI:
    return PostsAPI(env_config["base_url"])
"""

ROOT_CONFTEST_PY = """def pytest_xhtml_report_title(report):
    report.title = "Lounger Test Report"
"""

PYTEST_INI = """[pytest]
log_format = %(asctime)s | %(levelname)-8s | %(filename)s | %(message)s
log_date_format = %Y-%m-%d %H:%M:%S
disable_test_id_escaping_and_forfeit_all_rights_to_community_support = true
addopts = --html=./reports/result.html
"""

POSTS_API_PY = """from lounger.request import HttpRequest, api


class PostsAPI(HttpRequest):
    def __init__(self, base_url: str):
        super().__init__(base_url=base_url)

    @api(describe="Get a post", status_code=200)
    def get_post(self, post_id: int):
        return self.get(f"/posts/{post_id}")

    @api(describe="Create a post", status_code=201)
    def create_post(self, payload: dict):
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
        }
        return self.post("/posts", json=payload, headers=headers)
"""

TEST_PYTHON_CASE = '''import pytest
from pytest_req.assertions import expect

from lounger.utils.resource_loader import resource_file


@pytest.fixture(scope="module")
def create_post_payload() -> dict:
    return resource_file("create_post_payload.json")


def test_create_post(posts_api, create_post_payload: dict):
    post = posts_api.create_post(create_post_payload)

    expect(post).to_have_path_value("title", create_post_payload["title"])
    expect(post).to_have_path_value("body", create_post_payload["body"])
    expect(post).to_have_path_value("userId", create_post_payload["userId"])
'''

TEST_PYTHON_GET_CASE = '''import pytest
from pytest_req.assertions import expect


def test_get_post(posts_api):
    post = posts_api.get_post(1)

    expect(post).to_have_path_value("id", 1)
    expect(post).to_have_path_value("userId", 1)
'''

CREATE_POST_PAYLOAD = """{
  "title": "foo",
  "body": "bar",
  "userId": 1
}
"""


def create_project_scaffold(project_id: int) -> str:
    project_dir = PROJECTS_DIR / str(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)

    _ensure_dir(project_dir / "config")
    _ensure_dir(project_dir / "datas" / "sample")
    _ensure_dir(project_dir / "test_dir" / "posts_case")
    _ensure_dir(project_dir / "api" / "clients")
    _ensure_dir(project_dir / "reports" / "assets")
    _ensure_dir(project_dir / "logs")

    _write_file(project_dir / "config" / "config.yaml", CONFIG_YAML)
    _write_file(project_dir / "datas" / "sample" / "test_sample.yaml", SAMPLE_YAML)
    _write_file(project_dir / "test_api.py", TEST_API_PY)
    _write_file(project_dir / "conftest.py", ROOT_CONFTEST_PY)
    _write_file(project_dir / "pytest.ini", PYTEST_INI)
    _write_file(project_dir / "api" / "__init__.py", "")
    _write_file(project_dir / "api" / "clients" / "__init__.py", "")
    _write_file(project_dir / "api" / "clients" / "posts_api.py", POSTS_API_PY)
    _write_file(project_dir / "test_dir" / "__init__.py", "")
    _write_file(project_dir / "test_dir" / "conftest.py", TEST_DIR_CONFTEST_PY)
    _write_file(project_dir / "test_dir" / "posts_case" / "__init__.py", "")
    _write_file(project_dir / "test_dir" / "posts_case" / "test_create_post.py", TEST_PYTHON_CASE)
    _write_file(project_dir / "test_dir" / "posts_case" / "test_get_post.py", TEST_PYTHON_GET_CASE)
    _write_file(project_dir / "test_dir" / "test_data" / "create_post_payload.json", CREATE_POST_PAYLOAD)

    return str(project_dir.resolve())


def remove_project_scaffold(project_id: int):
    project_dir = PROJECTS_DIR / str(project_id)
    if project_dir.exists():
        import shutil
        shutil.rmtree(project_dir)


def _ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def _write_file(path: Path, content: str):
    path.write_text(content, encoding="utf-8")
