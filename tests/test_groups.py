import os
import sys
import unittest

pkg_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # noqa
sys.path.insert(0, pkg_root)  # noqa

from dcplib.aws.clients import clouddirectory as cd_client
from fusillade.errors import FusilladeHTTPException
from fusillade.directory import User, Group, cleanup_directory, cleanup_schema, \
    Role, clear_cd
from fusillade.directory.principal import default_group_policy_path
from fusillade.utils.json import get_json_file
from tests.common import new_test_directory, create_test_IAMPolicy, normalize_json
from tests.infra.testmode import standalone
from tests.json_mixin import AssertJSONMixin


@standalone
class TestGroup(unittest.TestCase, AssertJSONMixin):

    @classmethod
    def setUpClass(cls):
        cls.directory, cls.schema_arn = new_test_directory()
        cls.default_group_statement = normalize_json(get_json_file(default_group_policy_path))

    @classmethod
    def tearDownClass(cls):
        cleanup_directory(cls.directory._dir_arn)
        cleanup_schema(cls.schema_arn)

    def tearDown(self):
        clear_cd(self.directory)

    def test_create_group(self):
        with self.subTest("an error is returned when creating a group with an invalid statement."):
            with self.assertRaises(FusilladeHTTPException):
                group = Group.create("new_group1", {"random": "fields"})

        with self.subTest("The group is returned when the group has been created with default valid statement"):
            group = Group.create("new_group2")
            self.assertEqual(group.name, "new_group2")
            self.assertJSONEqual(group.get_policy(), self.default_group_statement)

        with self.subTest("The group is returned when the group has been created with specified valid statement."):
            group_name = "NewGroup1234"
            statement = create_test_IAMPolicy(group_name)
            group = Group.create("new_group3", statement)
            self.assertEqual(group.name, "new_group3")
            self.assertJSONEqual(group.get_policy(), statement)

    def test_policy(self):
        group = Group.create("new_group")
        with self.subTest("Only one policy is attached when lookup policy is called on a group without any roles"):
            policies = [p['policy_document'] for p in group.get_authz_params()['IAMPolicy']]
            self.assertEqual(len(policies), 1)
            self.assertJSONEqual(policies[0], self.default_group_statement)

        group_name = "NewGroup1234"
        statement = create_test_IAMPolicy(group_name)
        with self.subTest("The group policy changes when satement is set"):
            group.set_policy(statement)
            policies = [p['policy_document'] for p in group.get_authz_params()['IAMPolicy']]
            self.assertJSONEqual(policies[0], statement)

        with self.subTest("error raised when invalid statement assigned to group.get_policy()."):
            with self.assertRaises(FusilladeHTTPException):
                group.set_policy({"Statement": "Something else"})

    def test_users(self):
        emails = ["test@test.com", "why@not.com", "hello@world.com"]
        users = [User.provision_user(email).name for email in emails]
        with self.subTest("A user is added to the group when add_users is called"):
            group = Group.create("test")
            user = User.provision_user("another@place.com")
            group.add_users([user.name])
            actual_users = [i for i in group.get_users_iter()]
            self.assertEqual(len(actual_users), 1)
            self.assertEqual(User(object_ref=actual_users[0]).name, user.name)

        with self.subTest("Multiple users are added to the group when multiple users are passed to add_users"):
            group = Group.create("test2")
            group.add_users(users)
            actual_users = [i[1] for i in group.get_users_iter()]
            self.assertEqual(len(actual_users), 3)

        with self.subTest("Error returned when a user is added to a group it's already apart of."):
            group = Group.create("test3")
            group.add_users(users)
            try:
                group.add_users(users)
            except cd_client.exceptions.BatchWriteException:
                pass
            actual_users = [i[1] for i in group.get_users_iter()]
            self.assertEqual(len(actual_users), 3)

        with self.subTest("Error returned when adding a user that does not exist"):
            group = Group.create("test4")
            user = User("ghost_user@nowhere.com")
            try:
                group.add_users([user.name])
            except cd_client.exceptions.ResourceNotFoundException:
                pass

    def test_roles(self):
        roles = ['role1', 'role2']
        role_objs = [Role.create(name, create_test_IAMPolicy(name)) for name in roles]
        with self.subTest("multiple roles return when multiple roles are attached to group."):
            group = Group.create("test_roles")
            group.add_roles(roles)
            self.assertEqual(len(group.roles), 2)
        with self.subTest("policies inherited from roles are returned when lookup policies is called"):
            group_policies = sorted([normalize_json(p['policy_document']) for p in group.get_authz_params()['IAMPolicy']])
            role_policies = sorted([normalize_json(role.get_policy()) for role in role_objs] + [
                self.default_group_statement])
            self.assertListEqual(group_policies, role_policies)


if __name__ == '__main__':
    unittest.main()
