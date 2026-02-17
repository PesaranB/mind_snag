"""Tests for cluster groups reader."""

import numpy as np
from mind_snag.io.cluster_groups import read_cluster_groups


def test_read_tsv(tmp_path):
    tsv = tmp_path / "cluster_group.tsv"
    tsv.write_text(
        "cluster_id\tgroup\n"
        "0\tnoise\n"
        "1\tgood\n"
        "2\tmua\n"
        "3\tunsorted\n"
    )
    cids, cgs = read_cluster_groups(tsv)
    np.testing.assert_array_equal(cids, [0, 1, 2, 3])
    np.testing.assert_array_equal(cgs, [0, 2, 1, 3])


def test_read_csv(tmp_path):
    csv = tmp_path / "cluster_groups.csv"
    csv.write_text(
        "cluster_id,group\n"
        "5,good\n"
        "10,mua\n"
    )
    cids, cgs = read_cluster_groups(csv)
    np.testing.assert_array_equal(cids, [5, 10])
    np.testing.assert_array_equal(cgs, [2, 1])
