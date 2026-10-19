# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from camel.services import agent_openapi_server as module

ALICE_KEY = 'test-alice-' + 'a' * 32
BOB_KEY = 'test-bob-' + 'b' * 32
ROTATED_KEY = 'test-rotated-' + 'c' * 32
ROUTES = [
    ('POST', '/init', {'agent_id': 'private'}),
    ('GET', '/list_agent_ids', None),
    ('GET', '/history/private', None),
    ('POST', '/reset/private', None),
    ('POST', '/delete/private', None),
    ('POST', '/step/private', {'input_message': 'hello'}),
    ('POST', '/astep/private', {'input_message': 'hello'}),
]


class FakeAgent:
    def __init__(self, **kwargs):
        self.chat_history = [{'content': 'private history'}]
        self.reset = Mock()
        self.step = Mock(
            return_value=SimpleNamespace(
                model_dump=lambda: {'msgs': [{'content': 'owner reply'}]}
            )
        )
        self.kwargs = kwargs

    async def astep(self, **kwargs):
        return self.step(**kwargs)


@pytest.fixture
def server(monkeypatch):
    monkeypatch.setattr(
        module.ModelFactory, 'create', Mock(return_value=object())
    )
    monkeypatch.setattr(module, 'ChatAgent', FakeAgent)
    return module.ChatAgentOpenAPIServer(
        api_keys={
            ALICE_KEY: 'alice',
            BOB_KEY: 'bob',
            ROTATED_KEY: 'alice',
        }
    )


def client(server, key):
    return TestClient(
        server.get_app(), headers={'Authorization': 'Bearer ' + key}
    )


@pytest.mark.parametrize('method,path,payload', ROUTES)
@pytest.mark.parametrize('authorization', [None, 'Basic bad', 'Bearer bad'])
def test_all_seven_routes_authenticate_before_agent_operations(
    server, method, path, payload, authorization
):
    headers = {} if authorization is None else {'Authorization': authorization}
    response = TestClient(server.get_app()).request(
        method, '/v1/agents' + path, json=payload, headers=headers
    )
    assert response.status_code == 401
    assert response.headers['www-authenticate'] == 'Bearer'
    module.ModelFactory.create.assert_not_called()
    assert not server.agents


@pytest.mark.parametrize('method,path,payload', ROUTES)
def test_no_configuration_fails_closed(method, path, payload):
    server = module.ChatAgentOpenAPIServer()
    response = client(server, ALICE_KEY).request(
        method, '/v1/agents' + path, json=payload
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    'method,path,payload', [r for r in ROUTES if r[1] != '/list_agent_ids']
)
def test_other_identity_cannot_read_mutate_or_reinitialize_agent(
    server, method, path, payload
):
    alice = client(server, ALICE_KEY)
    assert (
        alice.post('/v1/agents/init', json={'agent_id': 'private'}).status_code
        == 200
    )
    agent = server.agents['private']
    response = client(server, BOB_KEY).request(
        method, '/v1/agents' + path, json=payload
    )
    assert response.status_code == 404
    assert server.agents['private'] is agent
    assert server._agent_owners['private'] == 'alice'
    agent.step.assert_not_called()
    agent.reset.assert_not_called()
    assert module.ModelFactory.create.call_count == 1


def test_owner_workflows_and_token_rotation(server):
    alice, bob = client(server, ALICE_KEY), client(server, BOB_KEY)
    for api, agent_id in [(alice, 'private'), (bob, 'bob-agent')]:
        assert (
            api.post(
                '/v1/agents/init', json={'agent_id': agent_id}
            ).status_code
            == 200
        )
    assert alice.get('/v1/agents/list_agent_ids').json() == {
        'agent_ids': ['private']
    }
    assert bob.get('/v1/agents/list_agent_ids').json() == {
        'agent_ids': ['bob-agent']
    }
    rotated = client(server, ROTATED_KEY)
    assert rotated.get('/v1/agents/history/private').json() == [
        {'content': 'private history'}
    ]
    for route in ['step', 'astep']:
        response = alice.post(
            f'/v1/agents/{route}/private', json={'input_message': 'hello'}
        )
        assert response.status_code == 200
        assert response.json()['msgs'][0]['content'] == 'owner reply'
    assert alice.post('/v1/agents/reset/private').status_code == 200
    server.agents['private'].reset.assert_called_once()
    assert alice.post('/v1/agents/delete/private').status_code == 200
    assert 'private' not in server._agent_owners
    assert alice.get('/v1/agents/history/private').status_code == 404
    assert (
        bob.post('/v1/agents/init', json={'agent_id': 'private'}).status_code
        == 200
    )
    assert alice.get('/v1/agents/history/private').status_code == 404


def test_token_in_query_is_not_authentication(server):
    response = TestClient(server.get_app()).get(
        '/v1/agents/list_agent_ids', params={'token': ALICE_KEY}
    )
    assert response.status_code == 401


def test_client_supplied_owner_cannot_override_identity(server):
    api = client(server, ALICE_KEY)
    response = api.post(
        '/v1/agents/init',
        json={
            'agent_id': 'private',
            'owner': 'bob',
            'user_id': 'bob',
        },
    )
    assert response.status_code == 200
    assert server._agent_owners['private'] == 'alice'


def test_unowned_injected_agent_is_not_accessible(server):
    server.agents['private'] = FakeAgent()
    api = client(server, ALICE_KEY)
    assert api.get('/v1/agents/history/private').status_code == 404
    assert api.get('/v1/agents/list_agent_ids').json() == {'agent_ids': []}


def test_concurrent_initialization_cannot_replace_another_owner(server):
    other = FakeAgent()

    def competing_create(**kwargs):
        with server._agents_lock:
            server.agents['private'] = other
            server._agent_owners['private'] = 'bob'
        return object()

    module.ModelFactory.create.side_effect = competing_create
    response = client(server, ALICE_KEY).post(
        '/v1/agents/init', json={'agent_id': 'private'}
    )
    assert response.status_code == 404
    assert server.agents['private'] is other
    assert server._agent_owners['private'] == 'bob'


@pytest.mark.parametrize(
    'mapping', [{'short': 'alice'}, {ALICE_KEY: ''}, {ALICE_KEY: None}]
)
def test_invalid_authentication_configuration_is_rejected(mapping):
    with pytest.raises(ValueError):
        module.ChatAgentOpenAPIServer(api_keys=mapping)


def test_router_inventory_is_protected(server):
    operations = [
        operation
        for path, methods in server.get_app().openapi()['paths'].items()
        if path.startswith('/v1/agents')
        for operation in methods.values()
    ]
    assert len(operations) == 7
    assert all(operation.get('security') for operation in operations)
