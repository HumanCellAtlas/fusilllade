from flask import request, make_response, jsonify

from fusillade import Group, Config
from fusillade.api._helper import _modify_roles, _modify_users
from fusillade.api.paging import get_next_token, get_page
from fusillade.utils.authorize import authorize, get_email_claim


@authorize(['fus:PostGroup'], ['arn:hca:fus:*:*:group'])
def post_group(token_info: dict):
    json_body = request.json
    group = Group.create(json_body['group_id'], statement=json_body.get('policy'),
                         creator=get_email_claim(token_info))
    group.add_roles(json_body.get('roles', []))  # Determine what response to return if roles don't exist
    return make_response(f"New role {json_body['group_id']} created.", 201)


@authorize(['fus:GetGroup'], ['arn:hca:fus:*:*:group'])
def get_groups(token_info: dict):
    next_token, per_page = get_next_token(request.args)
    return get_page(Group.list_all, next_token, per_page, 'groups')


@authorize(['fus:GetGroup'], ['arn:hca:fus:*:*:group/{group_id}/'], ['group_id'], {'fus:group_id': 'group_id'})
def get_group(token_info: dict, group_id: str):
    group = Group(group_id)
    return make_response(jsonify(group.get_info()), 200)


@authorize(['fus:PutGroup'], ['arn:hca:fus:*:*:group/{group_id}/policy'], ['group_id'], {'fus:group_id': 'group_id'})
def put_group_policy(token_info: dict, group_id: str):
    group = Group(group_id)
    group.set_policy(request.json['policy'])
    return make_response(f"{group_id} policy modified.", 200)


@authorize(['fus:GetUser'], ['arn:hca:fus:*:*:group/{group_id}/users'], ['group_id'], {'fus:group_id': 'group_id'})
def get_group_users(token_info: dict, group_id: str):
    next_token, per_page = get_next_token(request.args)
    group = Group(group_id)
    return get_page(group.get_users_page, next_token, per_page, 'users')


@authorize(['fus:GetRole'], ['arn:hca:fus:*:*:group/{group_id}/roles'], ['group_id'], {'fus:group_id': 'group_id'})
def get_groups_roles(token_info: dict, group_id: str):
    next_token, per_page = get_next_token(request.args)
    group = Group(group_id)
    return get_page(group.get_roles, next_token, per_page, 'roles')


@authorize(['fus:PutRole'], ['arn:hca:fus:*:*:group/{group_id}/roles'], ['group_id'], {'fus:group_id': 'group_id'})
def put_groups_roles(token_info: dict, group_id: str):
    group = Group(group_id)
    resp, code = _modify_roles(group, request)
    return make_response(jsonify(resp), code)


@authorize(['fus:DeleteGroup'], ['arn:hca:fus:*:*:group/{group_id}/'], ['group_id'], {'fus:group_id': 'group_id'})
def delete_group(token_info: dict, group_id):
    Group(group_id).delete_node()
    return make_response(f"{group_id} deleted.", 200)


@authorize(['fus:PutGroupUsers'],
           ['arn:hca:fus:*:*:group/{group_id}/users'],
           ['group_id'],
           {'fus:group_id': 'group_id'})
def put_groups_users(token_info: dict, group_id):
    group = Group(group_id)
    resp, code = _modify_users(group, request)
    return make_response(jsonify(resp), code)
