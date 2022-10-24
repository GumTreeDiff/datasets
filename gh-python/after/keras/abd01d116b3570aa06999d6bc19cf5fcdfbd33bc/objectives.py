import theano
import theano.tensor as T
import numpy as np

epsilon = 1.0e-15

def mean_squared_error(y_true, y_pred):
    return T.sqr(y_pred - y_true).mean()

def mean_absolute_error(y_true, y_pred):
    return T.abs_(y_pred - y_true).mean()

def squared_hinge(y_true, y_pred):
    return T.sqr(T.maximum(1. - y_true * y_pred, 0.)).mean()

def hinge(y_true, y_pred):
    return T.maximum(1. - y_true * y_pred, 0.).mean()

def categorical_crossentropy(y_true, y_pred):
    '''Expects a binary class matrix instead of a vector of scalar classes
    '''
    y_pred = T.clip(y_pred, epsilon, 1.0 - epsilon)
    # scale preds so that the class probas of each sample sum to 1
    y_pred /= y_pred.sum(axis=1, keepdims=True) 
    return T.nnet.categorical_crossentropy(y_pred, y_true).mean()

def binary_crossentropy(y_true, y_pred):
    y_pred = T.clip(y_pred, epsilon, 1.0 - epsilon)
    return T.nnet.binary_crossentropy(y_pred, y_true).mean()

# aliases
mse = MSE = mean_squared_error
mae = MAE = mean_absolute_error

from utils.generic_utils import get_from_module
def get(identifier):
    return get_from_module(identifier, globals(), 'objective')

def to_categorical(y):
    '''Convert class vector (integers from 0 to nb_classes)
    to binary class matrix, for use with categorical_crossentropy
    '''
    nb_classes = np.max(y)+1
    Y = np.zeros((len(y), nb_classes))
    for i in range(len(y)):
        Y[i, y[i]] = 1.
    return Y
