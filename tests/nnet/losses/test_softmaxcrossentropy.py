import hypothesis.extra.numpy as hnp
import hypothesis.strategies as st
import numpy as np
import pytest
from hypothesis import given
from numpy.testing import assert_allclose
from pytest import raises

import mygrad as mg
from mygrad import log
from mygrad.nnet.activations import softmax
from mygrad.nnet.losses import softmax_crossentropy
from mygrad.tensor_base import Tensor


@pytest.mark.parametrize(
    ("data", "labels"),
    [
        (np.ones((2,), dtype=float), np.zeros((2,), dtype=int)),  # 1D data
        (np.ones((2, 1), dtype=float), np.zeros((2,), dtype=float)),  # non-int labels
        (np.ones((2, 1), dtype=float), np.zeros((2, 1), dtype=int)),  # bad label-ndim
        (np.ones((2, 1), dtype=float), np.zeros((3,), dtype=int)),  # bad label-shape
    ],
)
def test_input_validation(data, labels):
    with raises((ValueError, TypeError)):
        softmax_crossentropy(data, labels)


@given(data=st.data(), labels_as_tensor=st.booleans())
def test_softmax_crossentropy(data: st.DataObject, labels_as_tensor: bool):
    s = data.draw(
        hnp.arrays(
            shape=hnp.array_shapes(max_side=10, min_dims=2, max_dims=2),
            dtype=float,
            elements=st.floats(-100, 100),
        )
    )
    y_true = data.draw(
        hnp.arrays(
            shape=(s.shape[0],),
            dtype=hnp.integer_dtypes(),
            elements=st.integers(min_value=0, max_value=s.shape[1] - 1),
        ).map(Tensor if labels_as_tensor else lambda x: x)
    )
    scores = Tensor(s)
    softmax_cross = softmax_crossentropy(scores, y_true, constant=False)
    softmax_cross.backward()

    mygrad_scores = Tensor(s)
    probs = softmax(mygrad_scores)

    correct_labels = (range(len(y_true)), y_true.data if labels_as_tensor else y_true)
    truth = np.zeros(mygrad_scores.shape)
    truth[correct_labels] = 1

    mygrad_cross = (-1 / s.shape[0]) * (log(probs) * truth).sum()
    mygrad_cross.backward()
    assert_allclose(softmax_cross.data, mygrad_cross.data, atol=1e-5, rtol=1e-5)
    assert_allclose(scores.grad, mygrad_scores.grad, atol=1e-5, rtol=1e-5)


@given(shape=st.sampled_from([(3, 1), (3, 4), tuple()]))
def test_bad_label_shape(shape):
    """
    Ensures that softmax_crossentropy checks for shape-(N,) `y_true`
    """
    scores = mg.arange(12).reshape(3, 4)
    labels = mg.zeros(shape, dtype=int)
    with raises(ValueError):
        softmax_crossentropy(scores, labels)


@given(type=st.sampled_from([bool, float, np.float32]))
def test_bad_label_type(type):
    """
    Ensures that softmax_crossentropy checks integer-type `y_true`
    """
    scores = mg.arange(12).reshape(3, 4)
    labels = np.zeros((3,), dtype=type)
    with raises(TypeError):
        softmax_crossentropy(scores, labels)
