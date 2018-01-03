import pytest
import numpy as np
from ersatz.pylearn.interface import _confusion_f1_score

def test_f1_perfect_prediction():
  values = np.repeat([1, 0, 2], 5)
  _, score = _confusion_f1_score(values, values, (0, 1, 2))
  assert np.allclose(score, 1)

def test_f1_missed_prediction():
  actual = np.repeat([1, 0], 5)
  predicted = np.repeat([0, 1], 5)
  _, score = _confusion_f1_score(predicted, actual, (0, 1))
  assert np.allclose(score, 0)

  actual = [1, 1, 1, 1, 1]
  predicted = [1, 0, 0, 0, 0]
  _, score = _confusion_f1_score(np.asarray(predicted), np.asarray(actual), (0, 1))

  assert np.allclose(score, 2.0*(1*0.2)/(1+0.2))
