'''
Kernels for assessing the similarity between MALDI-TOF spectra.
'''

from sklearn.gaussian_process.kernels import Hyperparameter
from sklearn.gaussian_process.kernels import StationaryKernelMixin
from sklearn.gaussian_process.kernels import Kernel

from sklearn.metrics import pairwise_distances
from sklearn.metrics import pairwise_kernels

from scipy.spatial.distance import cdist
from scipy.spatial.distance import pdist

import numpy as np
import sys


class DiffusionKernel(StationaryKernelMixin, Kernel):
    '''
    Implements a diffusion kernel that performs iterative smoothing of
    a MALDI-TOF spectrum.
    '''

    def __init__(self, sigma=1.0):
        '''
        Initialises a new instance of the kernel.

        Parameters:
            sigma: Smoothing parameter
        '''

        self.sigma = sigma

        def passthrough(*args, **kwargs):
            return args

        module = sys.modules['sklearn.metrics.pairwise']
        module.check_pairwise_arrays = passthrough

        sys.modules['sklearn.metrics.pairwise'] = module

    @property
    def hyperparameter_sigma(self):
        return Hyperparameter('sigma', 'numeric', self.sigma, 1)

    def __call__(self, X, Y=None, eval_gradient=False):
        '''
        Returns the kernel value k(X, Y) and, if desired, its gradient
        as well.

        Parameters
        ----------
        X : array, shape (n_samples_X, n_features)
            Left argument of the returned kernel k(X, Y)
        Y : array, shape (n_samples_Y, n_features), (optional, default=None)
            Right argument of the returned kernel k(X, Y). If None, k(X, X)
            if evaluated instead.
        eval_gradient : bool (optional, default=False)
            Determines whether the gradient with respect to the kernel
            hyperparameter is determined. Only supported when Y is None.

        Returns
        -------
        K : array, shape (n_samples_X, n_samples_Y)
            Kernel k(X, Y)
        K_gradient : array (opt.), shape (n_samples_X, n_samples_X, n_dims)
            The gradient of the kernel k(X, X) with respect to the
            hyperparameter of the kernel. Only returned when eval_gradient
            is True.
        '''

        def evaluate_kernel(x, y):

            x_positions = np.array(x[:, 0]).reshape(-1, 1)
            y_positions = np.array(y[:, 0]).reshape(-1, 1)

            distances = pairwise_distances(
                x_positions,
                y_positions,
                metric='sqeuclidean'
            )

            # Calculate scale factors as the outer product of the peak
            # heights of the input data.

            x_peaks = np.array(x[:, 1])
            y_peaks = np.array(y[:, 1])

            P = np.outer(x_peaks, y_peaks)
            K = P * np.exp(-distances / (8 * self.sigma))
            K = np.sum(K)

            # TODO: add other scale factors here
            return -K

        def evaluate_gradient(x, y):

            x_positions = np.array(x[:, 0]).reshape(-1, 1)
            y_positions = np.array(y[:, 0]).reshape(-1, 1)

            distances = pairwise_distances(
                x_positions,
                y_positions,
                metric='sqeuclidean'
            )

            # Calculate scale factors as the outer product of the peak
            # heights of the input data.

            x_peaks = np.array(x[:, 1])
            y_peaks = np.array(y[:, 1])

            P = np.outer(x_peaks, y_peaks)
            K = P * np.exp(-distances / (8 * self.sigma))

            # Thanks to the simple form of the kernel, the gradient only
            # requires an additional multiplication, followed by scaling
            # it appropriately.
            K_gradient = distances * K / (4 * self.sigma**2)

            # TODO: add other scale factors here
            return -np.sum(K_gradient)

        if Y is None:
            if eval_gradient:
                K = pairwise_kernels(X, metric=evaluate_kernel)
                K_gradient = pairwise_kernels(X, metric=evaluate_gradient)

                print(K_gradient.shape)
            else:
                return pairwise_kernels(X, metric=evaluate_kernel)
        else:

            # Following the original API here, which prohibits gradient
            # evaluation for this case.
            if eval_gradient:
                raise ValueError(
                    'Gradient can only be evaluated when Y is None.')

            return pairwise_kernels(X, Y, metric=evaluate_kernel)

    def diag(self, X):
        '''
        Returns the diagonal of the kernel k(X, X). The result of this
        method is identical to np.diag(self(X)); however, it can be
        evaluated more efficiently since only the diagonal is evaluated.

        Parameters
        ----------
        X : array, shape (n_samples_X, n_features)
            Left argument of the returned kernel k(X, Y)
        Returns
        -------
        K_diag : array, shape (n_samples_X,)
            Diagonal of kernel k(X, X)
        '''

        diag_values = np.zeros(len(X))

        for i, x in enumerate(X):
            x_positions = np.array(x[:, 0]).reshape(-1, 1)

            distances = pairwise_distances(
                x_positions,
                x_positions,
                metric='sqeuclidean'
            )

            x_peaks = np.array(x[:, 1])

            P = np.outer(x_peaks, x_peaks)
            K = P * np.exp(-distances / (8 * self.sigma))

            # TODO: add other scale factors here
            diag_values[i] = -np.sum(K)

        return diag_values

    def __repr__(self):
        return f'{self.__class__.__name__}({self.sigma:.2f})'
