#
#    Copyright 2019 EPAM Systems
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#

import json

import requests
from airflow.hooks.base_hook import BaseHook
from airflow.models import Connection
from legion.sdk.clients.model import ModelClient
from legion.sdk.clients.route import ModelRouteClient


class LegionHook(BaseHook):

    def __init__(self, edi_connection_id=None, model_connection_id=None):
        super().__init__(None)

        self.edi_connection_id = edi_connection_id
        self.model_connection_id = model_connection_id

    def get_edi_client(self, target_client_class):
        edi_conn = self.get_connection(self.edi_connection_id)
        self.log.info(edi_conn)

        return target_client_class(f'{edi_conn.schema}://{edi_conn.host}', self._get_token(edi_conn))

    def get_model_client(self, model_route_name: str) -> ModelClient:
        edi_conn = self.get_connection(self.edi_connection_id)
        self.log.info(edi_conn)

        model_conn = self.get_connection(self.model_connection_id)
        self.log.info(model_conn)

        mr_client: ModelRouteClient = self.get_edi_client(ModelRouteClient)
        model_route = mr_client.get(model_route_name)

        return ModelClient(model_route.status.edge_url, self._get_token(edi_conn))

    def _get_token(self, conn: Connection) -> str:
        """
        Authorize test user and get access token.

        :param Airlfow EDI connection TODO: add example configuration
        :return: access token
        """
        extra = json.loads(conn.extra)

        auth_url = extra["auth_url"]

        try:
            response = requests.post(
                auth_url,
                data={
                    'grant_type': 'password',
                    'client_id': extra["client_id"],
                    'client_secret': extra["client_secret"],
                    'username': conn.login,
                    'password': conn.password,
                    'scope': extra['scope']
                }
            )
            response_data = response.json()

            # Parse fields and return
            id_token = response_data.get('id_token')
            token_type = response_data.get('token_type')
            expires_in = response_data.get('expires_in')

            self.log.info('Received %s token with expiration in %d seconds', token_type, expires_in)

            return id_token
        except requests.HTTPError as http_error:
            raise Exception(f'Can not authorize user {conn.login} on {auth_url}: {http_error}') from http_error
