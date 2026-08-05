"""Regression tests for Release 21.19.1 API assignment scoping."""
from __future__ import annotations

import unittest
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.v1.router import list_projects, list_tasks
from app.auth.dependencies import Principal
from app.auth.permissions import Role
from app.database import Base
from app.models import (
    Freelancer,
    FreelancerAccount,
    HRAdminAccount,
    PortalProject,
    PortalProjectMember,
    PortalTask,
    PortalTaskAssignment,
    ProjectMember,
)


class ApiFreelancerScopeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.database = Session(self.engine, expire_on_commit=False)
        self.request = SimpleNamespace(
            state=SimpleNamespace(request_id="release-21.19.1-test")
        )
        self._seed()

    def tearDown(self) -> None:
        self.database.close()
        self.engine.dispose()

    def _seed(self) -> None:
        self.employee = Freelancer(
            freelancer_code="EMP-001",
            full_name="Assigned Employee",
            is_active=True,
        )
        self.other_employee = Freelancer(
            freelancer_code="EMP-002",
            full_name="Other Employee",
            is_active=True,
        )
        self.legacy_identity = Freelancer(
            freelancer_code="LEGACY-001",
            full_name="Assigned Employee Legacy",
            is_active=False,
        )
        self.database.add_all(
            [self.employee, self.other_employee, self.legacy_identity]
        )
        self.database.flush()

        self.employee_account = FreelancerAccount(
            freelancer_id=self.employee.id,
            username="assigned.employee",
            password_hash="test-hash",
            must_change_password=False,
            is_active=True,
        )
        self.other_account = FreelancerAccount(
            freelancer_id=self.other_employee.id,
            username="other.employee",
            password_hash="test-hash",
            must_change_password=False,
            is_active=True,
        )
        self.admin_account = HRAdminAccount(
            username="admin.test",
            display_name="Administrator",
            role="ADMIN",
            password_hash="test-hash",
            must_change_password=False,
            is_active=True,
        )
        self.database.add_all(
            [self.employee_account, self.other_account, self.admin_account]
        )
        self.database.flush()

        self.direct_project = PortalProject(
            project_code="DIRECT-001",
            name="Direct Assignment Project",
            status="ACTIVE",
        )
        self.mapped_project = PortalProject(
            project_code="MAPPED-001",
            name="Mapped Assignment Project",
            status="ACTIVE",
        )
        self.unrelated_project = PortalProject(
            project_code="OTHER-001",
            name="Unrelated Project",
            status="ACTIVE",
        )
        self.membership_only_project = PortalProject(
            project_code="MEMBER-001",
            name="Membership Only Project",
            status="ACTIVE",
        )
        self.database.add_all(
            [
                self.direct_project,
                self.mapped_project,
                self.unrelated_project,
                self.membership_only_project,
            ]
        )
        self.database.flush()

        self.direct_task = PortalTask(
            project_id=self.direct_project.id,
            title="Directly Assigned Task",
            status="IN_PROGRESS",
        )
        self.mapped_task = PortalTask(
            project_id=self.mapped_project.id,
            title="Legacy Mapped Task",
            status="NOT_STARTED",
        )
        self.unrelated_task = PortalTask(
            project_id=self.unrelated_project.id,
            title="Other Employee Task",
            status="IN_PROGRESS",
        )
        self.database.add_all(
            [self.direct_task, self.mapped_task, self.unrelated_task]
        )
        self.database.flush()

        self.database.add_all(
            [
                PortalTaskAssignment(
                    task_id=self.direct_task.id,
                    freelancer_id=self.employee.id,
                ),
                PortalTaskAssignment(
                    task_id=self.mapped_task.id,
                    freelancer_id=self.legacy_identity.id,
                ),
                PortalTaskAssignment(
                    task_id=self.unrelated_task.id,
                    freelancer_id=self.other_employee.id,
                ),
                PortalProjectMember(
                    project_id=self.membership_only_project.id,
                    freelancer_id=self.employee.id,
                    is_active=True,
                ),
                ProjectMember(
                    source_key="legacy:assigned-employee",
                    member_code="LEGACY-001",
                    member_name="Assigned Employee Legacy",
                    normalized_member_name="assigned employee legacy",
                    is_active=True,
                    source_freelancer_id=self.legacy_identity.id,
                    freelancer_id=self.employee.id,
                ),
            ]
        )
        self.database.commit()

        self.employee_principal = Principal(
            kind="employee",
            id=self.employee_account.id,
            role=Role.EMPLOYEE,
            account=self.employee_account,
        )
        self.other_principal = Principal(
            kind="employee",
            id=self.other_account.id,
            role=Role.EMPLOYEE,
            account=self.other_account,
        )
        self.admin_principal = Principal(
            kind="staff",
            id=self.admin_account.id,
            role=Role.ADMIN,
            account=self.admin_account,
        )

    def _project_ids(self, principal: Principal, **kwargs) -> set[int]:
        response = list_projects(
            request=self.request,
            limit=50,
            offset=0,
            status=kwargs.get("status"),
            database=self.database,
            principal=principal,
        )
        return {item.id for item in response.data}

    def _task_ids(self, principal: Principal, **kwargs) -> set[int]:
        response = list_tasks(
            request=self.request,
            limit=50,
            offset=0,
            project_id=kwargs.get("project_id"),
            status=kwargs.get("status"),
            database=self.database,
            principal=principal,
        )
        return {item.id for item in response.data}

    def test_employee_projects_include_direct_mapped_and_membership_only(self) -> None:
        self.assertEqual(
            self._project_ids(self.employee_principal),
            {
                self.direct_project.id,
                self.mapped_project.id,
                self.membership_only_project.id,
            },
        )

    def test_employee_projects_exclude_unrelated_project(self) -> None:
        self.assertNotIn(
            self.unrelated_project.id,
            self._project_ids(self.employee_principal),
        )

    def test_employee_tasks_include_direct_and_legacy_mapped_assignments(self) -> None:
        self.assertEqual(
            self._task_ids(self.employee_principal),
            {self.direct_task.id, self.mapped_task.id},
        )

    def test_employee_tasks_exclude_unrelated_assignment(self) -> None:
        self.assertNotIn(
            self.unrelated_task.id,
            self._task_ids(self.employee_principal),
        )

    def test_project_id_filter_cannot_bypass_employee_scope(self) -> None:
        self.assertEqual(
            self._task_ids(
                self.employee_principal,
                project_id=self.unrelated_project.id,
            ),
            set(),
        )

    def test_status_filter_remains_compatible_with_employee_scope(self) -> None:
        self.assertEqual(
            self._task_ids(self.employee_principal, status="IN_PROGRESS"),
            {self.direct_task.id},
        )

    def test_other_employee_receives_only_their_assignment(self) -> None:
        self.assertEqual(
            self._project_ids(self.other_principal),
            {self.unrelated_project.id},
        )
        self.assertEqual(
            self._task_ids(self.other_principal),
            {self.unrelated_task.id},
        )

    def test_staff_access_remains_unrestricted(self) -> None:
        self.assertEqual(
            self._project_ids(self.admin_principal),
            {
                self.direct_project.id,
                self.mapped_project.id,
                self.unrelated_project.id,
                self.membership_only_project.id,
            },
        )
        self.assertEqual(
            self._task_ids(self.admin_principal),
            {self.direct_task.id, self.mapped_task.id, self.unrelated_task.id},
        )

    def test_misconfigured_staff_employee_role_fails_closed(self) -> None:
        malformed_principal = Principal(
            kind="staff",
            id=self.admin_account.id,
            role=Role.EMPLOYEE,
            account=self.admin_account,
        )
        self.assertEqual(self._project_ids(malformed_principal), set())
        self.assertEqual(self._task_ids(malformed_principal), set())


if __name__ == "__main__":
    unittest.main()
