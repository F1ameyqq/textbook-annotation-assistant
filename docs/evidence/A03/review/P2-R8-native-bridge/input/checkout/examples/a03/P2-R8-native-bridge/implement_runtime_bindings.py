"""Local explicit native propagation; preserve old format constants/defaults."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def edit(path, pairs):
    file = ROOT / path
    value = file.read_text(encoding='utf-8')
    for old, new in pairs:
        if old not in value:
            raise RuntimeError('missing source anchor: ' + path + ': ' + old[:60])
        value = value.replace(old, new)
    file.write_bytes(value.encode('utf-8'))


if __name__ == '__main__':
    edit('src/annotation/delivery/mock/persistent.py', [
        ('class PersistentMockSession:\n', 'class PersistentMockSession:\n    _format = FORMAT\n    _application_id = APPLICATION_ID\n    _user_version = 1\n    _native = False\n'),
        ('if snapshot.schema_version != "1.1.0-a-recovery-proposal":', 'if snapshot.schema_version != ("1.4.0-a03-native-proposal" if cls._native else "1.1.0-a-recovery-proposal"):'),
        ('{"format": FORMAT, "user_version": 1, "application_id": APPLICATION_ID,', '{"format": cls._format, "user_version": cls._user_version, "application_id": cls._application_id,'),
        ('        state = {"base": _plain(snapshot)', '        if cls._native:\n            descriptor["native_adoption"] = cls.native_metadata()\n        state = {"base": _plain(snapshot)'),
        ('str(APPLICATION_ID))\n                db.execute("PRAGMA user_version=1")', 'str(cls._application_id))\n                db.execute("PRAGMA user_version=" + str(cls._user_version))'),
        ('            session = cls(directory, descriptor)\n            return session', '            session = cls(directory, descriptor)\n            session._bridge_context = bridge_context\n            return session'),
        ('!= APPLICATION_ID or db.execute("PRAGMA user_version").fetchone()[0] != 1:', '!= cls._application_id or db.execute("PRAGMA user_version").fetchone()[0] != cls._user_version:'),
        ('if descriptor.get("format") != FORMAT:', 'if descriptor.get("format") != cls._format:'),
        ('        return cls(directory, descriptor)', '        if cls._native and descriptor.get("native_adoption") != cls.native_metadata():\n            reject("NATIVE_TARGET_ADOPTION_MISMATCH", "target native metadata is incomplete or foreign")\n        session = cls(directory, descriptor)\n        session._bridge_context = bridge_context\n        return session'),
        # _connect is an instance method, so it cannot consult the classmethod local.
        ('if db.execute("PRAGMA application_id").fetchone()[0] != cls._application_id or db.execute("PRAGMA user_version").fetchone()[0] != cls._user_version:\n                db.close()', 'if db.execute("PRAGMA application_id").fetchone()[0] != self._application_id or db.execute("PRAGMA user_version").fetchone()[0] != self._user_version:\n                db.close()'),
        ('            for name in ("store_id", "target_session_id", "target_key", "directory", "fixed_source_ref", "fixed_scope_id"):', '            if self._native and descriptor.get("native_adoption") != self.native_metadata():\n                db.close()\n                reject("NATIVE_TARGET_ADOPTION_MISMATCH", "target native adoption changed")\n            for name in ("store_id", "target_session_id", "target_key", "directory", "fixed_source_ref", "fixed_scope_id"):')])
    edit('src/annotation/runtime/storage/__init__.py', [
        ('class RuntimeStore(HoldSupport):\n', 'class RuntimeStore(HoldSupport):\n    _db_version = DB_VERSION\n    _application_id = 0x41303352\n    _user_version = 1\n\n    def bridge_for(self, bundle, root=None):\n        return None\n\n    def _validate(self, bundle, *, asset_root):\n        from annotation.contracts import validate_recovery_bundle\n        return validate_recovery_bundle(bundle, asset_root=asset_root, bridge_context=self.bridge_for(bundle, asset_root))\n\n    def _expected_meta(self):\n        return {"version": self._db_version, "ledger_id": self.ledger_id,\n            "target_store_id": self.target_store_id, "state_dir": str(self.directory)}\n'),
        ('self.anchor.get("db_version") != DB_VERSION', 'self.anchor.get("db_version") != self._db_version'),
        ('meta != {"version": DB_VERSION, "ledger_id": self.ledger_id, "target_store_id": self.target_store_id,\n                            "state_dir": str(self.directory)}', 'meta != self._expected_meta()'),
        ('!= 0x41303352 or connection.execute("PRAGMA user_version").fetchone()[0] != 1:', '!= self._application_id or connection.execute("PRAGMA user_version").fetchone()[0] != self._user_version:'),
        ('validated = validate_recovery_bundle(bundle, asset_root=asset_root)', 'validated = self._validate(bundle, asset_root=asset_root)'),
        ('bundle = validate_recovery_bundle(self.bundle(registration_id), asset_root=reg["package_root"])', 'bundle = self._validate(self.bundle(registration_id), asset_root=reg["package_root"])'),
        ('assert_recovery_plan_ready(bundle, plan_ref, plan["payload"]["snapshot"])', 'assert_recovery_plan_ready(bundle, plan_ref, plan["payload"]["snapshot"], bridge_context=self.bridge_for(bundle, reg["package_root"]))'),
        ('snapshot = plain(observer.snapshot_from_observation(observation))', 'snapshot = plain(observer.snapshot_from_observation(observation, bridge_context=self.bridge_for(self.bundle(registration_id), self.registration(registration_id)["package_root"])))'),
        ('validate_recovery_bundle(candidate, asset_root=self.registration(registration_id)["package_root"])', 'self._validate(candidate, asset_root=self.registration(registration_id)["package_root"])'),
        ('validate_recovery_bundle(candidate, asset_root=reg["package_root"])', 'self._validate(candidate, asset_root=reg["package_root"])')])
