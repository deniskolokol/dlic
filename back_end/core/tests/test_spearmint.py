import pytest
from collections import OrderedDict
from ersatz import spearmint_wrapper


@pytest.fixture
def fixtures():
    proj = 'example'
    conf = OrderedDict({"X" : {"name":"X", "type":"float", "min":0, "max":1, "size":2}})
    experiments = ['.1  50.    0.1796875 0.3046875',
                   '.05 49.896 0.6796875 0.8046875']
    return proj, conf, experiments


def test_predict_params_tmp_proj(fixtures):
    # Using all default parameters except of the chooser type.
    proj, conf, experiments = fixtures
    opts = {'chooser_module': 'GPEIChooser'}
    spw = spearmint_wrapper.SpearmintLightWrapper(project_name=proj,
                                                  config=conf,
                                                  opts=opts)
    result = spw.perform(experiments)
    assert len(result) == 3
