"""Tests functions in the CSV Uploader Flask Blueprint."""
import json
import os
from collections import OrderedDict

from multinet.util import test_data_path
from multinet.uploaders.d3_json import validate_d3_json

TEST_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))


def test_validate_d3_json():
    """Tests the validate_csv function."""
    # Arrange: Set file paths
    # good_file = os.path.join(TEST_DATA_DIR, "miserables.json")
    duplicated_nodes = os.path.join(TEST_DATA_DIR, "miserables_duplicate_nodes.json")
    incon_keys = os.path.join(TEST_DATA_DIR, "miserables_inconsistent_link_keys.json")
    inval_keys = os.path.join(TEST_DATA_DIR, "miserables_invalid_link_keys.json")

    # Arrange: Import the les miserables datasets with and without errors
    with open(test_data_path("miserables.json")) as f:
        good_data = json.load(f, object_pairs_hook=OrderedDict)
    with open(duplicated_nodes) as f:
        dup_node_data = json.load(f, object_pairs_hook=OrderedDict)
    with open(incon_keys) as f:
        incon_keys = json.load(f, object_pairs_hook=OrderedDict)
    with open(inval_keys) as f:
        inval_keys = json.load(f, object_pairs_hook=OrderedDict)

    # Act: Test all the data files and save their outcomes
    outcome1 = validate_d3_json(good_data)
    outcome2 = validate_d3_json(dup_node_data)
    outcome3 = validate_d3_json(incon_keys)
    outcome4 = validate_d3_json(inval_keys)

    # Assert: Check the outcomes against what we expect
    assert len(outcome1) == 0

    assert outcome2[0] == {"error": "node_duplicates"}
    assert len(outcome2) == 1

    assert outcome3[0] == {"error": "inconsistent_link_keys"}
    assert len(outcome3) == 1

    print(outcome4)
    assert outcome4[0] == {"error": "invalid_link_keys"}
    assert outcome4[1] == {"error": "inconsistent_link_keys"}
    assert len(outcome4) == 2
