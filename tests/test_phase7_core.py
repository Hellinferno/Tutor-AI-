from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "studylab_core"))

from studylab_core import SqliteStudyLabStore, StudyLabAPI  # noqa: E402

SAMPLE = "Gradient descent moves opposite the gradient of the loss. Theta := theta - eta * gradient."


class _EnvGuard:
    def __init__(self, **values: str) -> None:
        self.values = values
        self._saved: dict[str, str | None] = {}

    def __enter__(self):
        for k, v in self.values.items():
            self._saved[k] = os.environ.get(k)
            os.environ[k] = v
        return self

    def __exit__(self, *exc):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _accounts(api: StudyLabAPI):
    owner = api.register_user("owner@x.com", "password1")["user"]
    viewer = api.register_user("viewer@x.com", "password2")["user"]
    editor = api.register_user("editor@x.com", "password3")["user"]
    return owner, viewer, editor


# ── Sharing ────────────────────────────────────────────────────────────────

class Phase7SharingTests(unittest.TestCase):
    def test_share_and_list(self) -> None:
        api = StudyLabAPI()
        owner, viewer, _ = _accounts(api)
        nb = api.create_notebook("Group", user_id=owner["id"])
        share = api.share_notebook(owner["id"], nb["id"], "viewer@x.com", "viewer")
        self.assertEqual(share["role"], "viewer")
        self.assertEqual(share["shared_with_email"], "viewer@x.com")
        self.assertEqual(len(api.list_shares(owner["id"], nb["id"])["shares"]), 1)

    def test_shared_with_me(self) -> None:
        api = StudyLabAPI()
        owner, viewer, _ = _accounts(api)
        nb = api.create_notebook("Group", user_id=owner["id"])
        api.share_notebook(owner["id"], nb["id"], "viewer@x.com", "viewer")
        mine = api.list_shared_with_me(viewer["id"])["shared_with_me"]
        self.assertEqual(len(mine), 1)
        self.assertEqual(mine[0]["title"], "Group")
        self.assertEqual(mine[0]["role"], "viewer")

    def test_resharing_updates_role(self) -> None:
        api = StudyLabAPI()
        owner, viewer, _ = _accounts(api)
        nb = api.create_notebook("Group", user_id=owner["id"])
        api.share_notebook(owner["id"], nb["id"], "viewer@x.com", "viewer")
        api.share_notebook(owner["id"], nb["id"], "viewer@x.com", "editor")
        shares = api.list_shares(owner["id"], nb["id"])["shares"]
        self.assertEqual(len(shares), 1)  # not duplicated
        self.assertEqual(shares[0]["role"], "editor")

    def test_unshare(self) -> None:
        api = StudyLabAPI()
        owner, viewer, _ = _accounts(api)
        nb = api.create_notebook("Group", user_id=owner["id"])
        s = api.share_notebook(owner["id"], nb["id"], "viewer@x.com", "viewer")
        api.unshare_notebook(owner["id"], nb["id"], s["id"])
        self.assertEqual(api.list_shares(owner["id"], nb["id"])["shares"], [])

    def test_share_unknown_email_rejected(self) -> None:
        api = StudyLabAPI()
        owner, _, _ = _accounts(api)
        nb = api.create_notebook("Group", user_id=owner["id"])
        with self.assertRaises(KeyError):
            api.share_notebook(owner["id"], nb["id"], "ghost@x.com", "viewer")

    def test_share_bad_role_rejected(self) -> None:
        api = StudyLabAPI()
        owner, _, _ = _accounts(api)
        nb = api.create_notebook("Group", user_id=owner["id"])
        with self.assertRaises(ValueError):
            api.share_notebook(owner["id"], nb["id"], "viewer@x.com", "owner")

    def test_non_owner_cannot_share_or_list(self) -> None:
        api = StudyLabAPI()
        owner, viewer, _ = _accounts(api)
        nb = api.create_notebook("Group", user_id=owner["id"])
        with self.assertRaises(PermissionError):
            api.share_notebook(viewer["id"], nb["id"], "editor@x.com", "viewer")
        with self.assertRaises(PermissionError):
            api.list_shares(viewer["id"], nb["id"])


# ── Authorization (view vs edit) ────────────────────────────────────────────

class Phase7AuthorizationTests(unittest.TestCase):
    def _setup(self, api: StudyLabAPI):
        owner, viewer, editor = _accounts(api)
        nb = api.create_notebook("Group", user_id=owner["id"])
        api.share_notebook(owner["id"], nb["id"], "viewer@x.com", "viewer")
        api.share_notebook(owner["id"], nb["id"], "editor@x.com", "editor")
        return owner, viewer, editor, nb

    def test_owner_full_access(self) -> None:
        api = StudyLabAPI()
        owner, _, _, nb = self._setup(api)
        self.assertTrue(api.authorize_notebook(owner["id"], nb["id"], require_edit=True))

    def test_viewer_read_only(self) -> None:
        api = StudyLabAPI()
        _, viewer, _, nb = self._setup(api)
        self.assertTrue(api.authorize_notebook(viewer["id"], nb["id"]))
        with self.assertRaises(PermissionError):
            api.authorize_notebook(viewer["id"], nb["id"], require_edit=True)

    def test_editor_can_edit(self) -> None:
        api = StudyLabAPI()
        _, _, editor, nb = self._setup(api)
        self.assertTrue(api.authorize_notebook(editor["id"], nb["id"], require_edit=True))

    def test_stranger_denied(self) -> None:
        api = StudyLabAPI()
        _, _, _, nb = self._setup(api)
        stranger = api.register_user("stranger@x.com", "password9")["user"]
        with self.assertRaises(PermissionError):
            api.authorize_notebook(stranger["id"], nb["id"])


# ── Roles / admin ────────────────────────────────────────────────────────────

class Phase7RoleTests(unittest.TestCase):
    def test_admin_role_via_env(self) -> None:
        with _EnvGuard(STUDYLAB_ADMIN_EMAILS="boss@x.com"):
            api = StudyLabAPI()
            boss = api.register_user("boss@x.com", "password1")["user"]
            student = api.register_user("kid@x.com", "password2")["user"]
            self.assertEqual(boss["role"], "admin")
            self.assertEqual(student["role"], "student")

    def test_admin_can_list_users(self) -> None:
        with _EnvGuard(STUDYLAB_ADMIN_EMAILS="boss@x.com"):
            api = StudyLabAPI()
            boss = api.register_user("boss@x.com", "password1")["user"]
            api.register_user("kid@x.com", "password2")
            users = api.list_users(boss["id"])["users"]
            self.assertEqual(len(users), 2)
            self.assertTrue(all("password_hash" not in u for u in users))

    def test_non_admin_cannot_list_users(self) -> None:
        api = StudyLabAPI()
        student = api.register_user("kid@x.com", "password2")["user"]
        with self.assertRaises(PermissionError):
            api.list_users(student["id"])


# ── Persistence + cascade ─────────────────────────────────────────────────────

class Phase7PersistenceTests(unittest.TestCase):
    def test_share_survives_reopen_and_role_persists(self) -> None:
        path = str(Path(tempfile.mkdtemp()) / "p7.db")
        with _EnvGuard(STUDYLAB_ADMIN_EMAILS="boss@x.com"):
            api = StudyLabAPI(SqliteStudyLabStore(path))
            owner = api.register_user("owner@x.com", "password1")["user"]
            api.register_user("viewer@x.com", "password2")
            boss = api.register_user("boss@x.com", "password3")["user"]
            nb = api.create_notebook("N", user_id=owner["id"])
            api.share_notebook(owner["id"], nb["id"], "viewer@x.com", "editor")
            api.store.close()

            reopened = StudyLabAPI(SqliteStudyLabStore(path))
            self.assertEqual(len(reopened.list_shares(owner["id"], nb["id"])["shares"]), 1)
            self.assertEqual(reopened.store.require_user(boss["id"]).role, "admin")
            reopened.store.close()

    def test_owner_deletion_removes_shares(self) -> None:
        api = StudyLabAPI()
        owner, viewer, _ = _accounts(api)
        nb = api.create_notebook("N", user_id=owner["id"])
        api.share_notebook(owner["id"], nb["id"], "viewer@x.com", "viewer")
        api.delete_account(owner["id"])
        self.assertEqual(api.store.shares_for_user(viewer["id"]), [])


if __name__ == "__main__":
    unittest.main()
