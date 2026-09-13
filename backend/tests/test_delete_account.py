import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import IssueModel, NotificationModel, ResourceModel, ScanModel, UserModel
from app.services.auth import delete_user_account


class DeleteAccountTests(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        self.SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    def test_delete_user_account_removes_only_that_users_data(self) -> None:
        with self.SessionLocal() as db:
            user = UserModel(email="owner@example.com", password_hash="hash")
            other_user = UserModel(email="other@example.com", password_hash="hash")
            db.add_all([user, other_user])
            db.commit()
            db.refresh(user)
            db.refresh(other_user)

            owned_resource = ResourceModel(owner_key=f"user:{user.id}", name="Owned", url="https://owned.example")
            other_resource = ResourceModel(owner_key=f"user:{other_user.id}", name="Other", url="https://other.example")
            db.add_all([owned_resource, other_resource])
            db.commit()
            db.refresh(owned_resource)
            db.refresh(other_resource)

            db.add_all(
                [
                    ScanModel(resource_id=owned_resource.id, classification="ok"),
                    IssueModel(
                        resource_id=owned_resource.id,
                        issue_type="http_error",
                        severity="high",
                        message="Broken",
                    ),
                    NotificationModel(
                        owner_key=f"user:{user.id}",
                        resource_id=owned_resource.id,
                        severity="high",
                        title="Broken link",
                        message="Owned link failed",
                    ),
                    ScanModel(resource_id=other_resource.id, classification="ok"),
                    IssueModel(
                        resource_id=other_resource.id,
                        issue_type="http_error",
                        severity="high",
                        message="Other broken",
                    ),
                    NotificationModel(
                        owner_key=f"user:{other_user.id}",
                        resource_id=other_resource.id,
                        severity="high",
                        title="Other broken link",
                        message="Other link failed",
                    ),
                ]
            )
            db.commit()

            delete_user_account(db, user)

            self.assertIsNone(db.scalar(select(UserModel).where(UserModel.email == "owner@example.com")))
            self.assertIsNone(db.scalar(select(ResourceModel).where(ResourceModel.name == "Owned")))
            self.assertEqual(db.scalars(select(ScanModel).where(ScanModel.resource_id == owned_resource.id)).all(), [])
            self.assertEqual(db.scalars(select(IssueModel).where(IssueModel.resource_id == owned_resource.id)).all(), [])
            self.assertEqual(db.scalars(select(NotificationModel).where(NotificationModel.owner_key == f"user:{user.id}")).all(), [])

            self.assertIsNotNone(db.scalar(select(UserModel).where(UserModel.email == "other@example.com")))
            self.assertIsNotNone(db.scalar(select(ResourceModel).where(ResourceModel.name == "Other")))
            self.assertEqual(len(db.scalars(select(ScanModel).where(ScanModel.resource_id == other_resource.id)).all()), 1)
            self.assertEqual(len(db.scalars(select(IssueModel).where(IssueModel.resource_id == other_resource.id)).all()), 1)
            self.assertEqual(
                len(db.scalars(select(NotificationModel).where(NotificationModel.owner_key == f"user:{other_user.id}")).all()),
                1,
            )


if __name__ == "__main__":
    unittest.main()
