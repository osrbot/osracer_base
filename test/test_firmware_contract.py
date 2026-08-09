import json
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "test/fixtures/proto_1_1/firmware_contract.json"
PROFILE_DIR = ROOT / "config/vehicles"


class PublicFirmwareContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_contract_is_minimal_and_sanitized(self):
        self.assertEqual(
            set(self.contract), {"schema_version", "protocol", "command", "profiles"}
        )
        self.assertEqual(self.contract["schema_version"], 1)
        self.assertEqual(self.contract["protocol"], "1.1")
        self.assertEqual(
            self.contract["command"],
            {
                "name": "v",
                "linear_velocity_unit": "m/s",
                "steering_angle_unit": "deg",
            },
        )
        self.assertEqual(set(self.contract["profiles"]), {"blue", "neo", "red"})

        serialized = json.dumps(self.contract, sort_keys=True).lower()
        for private_field in (
            "gpio",
            "encoder",
            "hardware",
            "manufacturer",
            "nvs",
            "pid",
            "pwm",
            "product_name",
            "wheel_radius",
        ):
            self.assertNotIn(private_field, serialized)

    def test_ros_profiles_match_public_firmware_identity(self):
        for profile_id, firmware in self.contract["profiles"].items():
            with self.subTest(profile=profile_id):
                ros_document = yaml.safe_load(
                    (PROFILE_DIR / f"{profile_id}.yaml").read_text(encoding="utf-8")
                )
                ros_profile = ros_document["/**"]["ros__parameters"]
                self.assertEqual(ros_profile["vehicle_profile"], profile_id)
                self.assertEqual(
                    ros_profile["profile_schema"], firmware["profile_schema"]
                )


if __name__ == "__main__":
    unittest.main()
