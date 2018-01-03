from ersatz.shared.cifar import BatchWriter


def test_batch_size_max():
    bw = BatchWriter('', max_batch_size=10000)
    size = bw.calculate_batch_size(60000)
    assert size == 10000


def test_batch_size_not_eq():
    bw = BatchWriter('', max_batch_size=10000)
    size = bw.calculate_batch_size(43123)
    assert size == 8624


def test_batch_size_lt_max():
    bw = BatchWriter('', max_batch_size=10000)
    size = bw.calculate_batch_size(8000)
    assert size == 8000
