import mock
from dmworker import parser


def test_unl_zip_bug():
    notify = mock.MagicMock()
    meta = parser.run('fixtures/dmworker/ul_zip_bug.zip', notify)
    assert meta == {
        'archive_path': 'TRAINING_3.ts',
        'data_rows': 3275,
        'version': 3,
        'data_type': 'TIMESERIES',
        'binary_input': False,
        'key': 'fixtures/dmworker/ul_zip_bug.zip',
        'empty_rows': 3275,
        'binary_output': True,
        'output_size': 5,
        'max_timesteps': 348,
        'min_timesteps': 1,
        'classes': {
            '0': 96253,
            '1': 96442,
            '2': 96293,
            '3': 96499,
            '4': 96282
        },
        'input_size': 12,
        'size': 19962498
    }
