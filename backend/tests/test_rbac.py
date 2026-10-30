"""Role based access control tests for the HR endpoints

Each test is parametrized over HR_GET_ROUTES
Every route in that list is checked against both roles
"""

import pytest

# Every GET route restricted to the hr_admin role
# Add new HR routes covered by both tests
HR_GET_ROUTES = ["/api/hr/verify"]


@pytest.mark.parametrize("path", HR_GET_ROUTES)
def test_employee_gets_403_on_every_hr_route(client, make_user, login, path):
    """A logged in regular employee is forbidden from HR routes

    403: the user is authenticated but lacks the role
    """
    # defaults to role="employee"
    make_user("alice")  
    assert client.get(path, headers=login("alice")).status_code == 403


@pytest.mark.parametrize("path", HR_GET_ROUTES)
def test_hr_admin_gets_200_on_every_hr_route(client, make_user, login, path):
    """An hr_admin user can access every HR route"""
    make_user("boss", role="hr_admin")
    assert client.get(path, headers=login("boss")).status_code == 200
