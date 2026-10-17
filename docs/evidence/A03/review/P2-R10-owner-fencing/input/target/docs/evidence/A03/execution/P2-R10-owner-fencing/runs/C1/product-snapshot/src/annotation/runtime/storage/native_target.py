"""Separate, fresh-only target format. No old database migration or reset."""
from annotation.contracts.a03_native import select_native_codec, require_context
from annotation.delivery.mock.persistent import PersistentMockSession


class NativeTargetSession(PersistentMockSession):
    _native = True
    _format = 'a03-native-target-db-1'
    _application_id = 0x41303454
    _user_version = 4

    @staticmethod
    def native_metadata():
        selection = select_native_codec()
        return {'format': 'a03-native-target-adoption-1', 'profile': selection.profile_id,
            'profile_sha256': selection.profile_sha256, 'adoption_sha256': selection.adoption_sha256,
            'initialization': 'COMPLETE', 'migration': 'NOT_IMPLEMENTED_BLOCKED'}

    def snapshot_from_observation(self, observation, *, bridge_context=None):
        context = bridge_context or getattr(self, '_bridge_context', None)
        require_context(context)
        return super().snapshot_from_observation(observation, bridge_context=context)

    def verify_prepared_action(self, prepared, *, observation_binding=None,
                               expected_config_version=None, expected_plan_ref=None, bridge_context=None):
        context = bridge_context or getattr(prepared.get('bundle'), 'bridge_context', None)
        require_context(context, prepared['bundle'])
        return super().verify_prepared_action(prepared, observation_binding=observation_binding,
            expected_config_version=expected_config_version, expected_plan_ref=expected_plan_ref,
            bridge_context=context)

    def synthetic_external_add_directory(self, directory_id):
        """Explicit fixture operator action to model external target drift.

        This does not create/reset annotation fields, intents, permits or runs.
        It is confined to this fresh synthetic target format.
        """
        if not isinstance(directory_id, str) or not directory_id.startswith('synthetic-external-'):
            raise ValueError('explicit synthetic external directory identity required')
        with self._connect() as connection:
            connection.execute('BEGIN IMMEDIATE')
            state = self._load(connection)
            if directory_id in state['target']['directories']:
                raise ValueError('external operation identity already exists')
            state['target']['directories'].append(directory_id)
            state['epoch'] += 1
            self._save(connection, state)
