# Adapted from the original Sequential Learning App
# https://github.com/BAMresearch/SequentialLearningApp
import numpy as np
import pandas as pd
from scipy.spatial import distance_matrix
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel

from slamd.common.error_handling import ValueNotSupportedException, SequentialLearningException
from slamd.discovery.processing.algorithms.experiment_postprocessor import ExperimentPostprocessor
from slamd.discovery.processing.algorithms.experiment_preprocessor import ExperimentPreprocessor
from slamd.discovery.processing.algorithms.slamd_random_forest import SlamdRandomForest
from slamd.discovery.processing.models.model_type import ModelType


# Attention - suppressing expected Gaussian Regressor warnings
import warnings
from sklearn.exceptions import ConvergenceWarning
warnings.filterwarnings("ignore", category=ConvergenceWarning)


class ExperimentConductor:

    @classmethod
    def run(cls, exp):
        ExperimentPreprocessor.preprocess(exp)
        cls.fit_model(exp)
        utility = cls.update_index_MLI(exp)
        novelty = cls.compute_novelty_factor(exp)

        return ExperimentPostprocessor.postprocess(exp, utility, novelty)

    @classmethod
    def fit_model(cls, exp):
        if exp.model == ModelType.RANDOM_FOREST.value:
            regressor = SlamdRandomForest()
        elif exp.model == ModelType.GAUSSIAN_PROCESS.value:
            # Hyperparameters from Christoph
            kernel = ConstantKernel(1.0, (1e-3, 1e3)) * RBF(10, (1e-2, 1e2))
            regressor = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=9, random_state=42)
        else:
            raise ValueNotSupportedException(message=f'Invalid model: {exp.model}')

        predictions = {}
        uncertainties = {}
        for target in exp.target_names:
            # Train the model for every target with the corresponding rows and labels
            training_rows = exp.features_df.loc[exp.label_index].values
            training_labels = exp.targets_df.loc[exp.label_index, target].values

            regressor.fit(training_rows, training_labels)

            # Predict the label for the remaining rows
            rows_to_predict = exp.features_df.loc[exp.nolabel_index].values
            prediction, uncertainty = regressor.predict(rows_to_predict, return_std=True)

            predictions[target] = prediction
            uncertainties[target] = uncertainty

        exp.prediction = pd.DataFrame(predictions, index=exp.nolabel_index)
        exp.uncertainty = pd.DataFrame(uncertainties, index=exp.nolabel_index)

    @classmethod
    def update_index_MLI(cls, exp):
        # The strategy is always 'MLI (explore & exploit)' for this implementation
        # See the original app for other possibilities

        # Clip predicted values with thresholds for utility calculation
        clipped_prediction = cls.clip_prediction(exp)

        # Mean and stdev of supplied labels for normalization - use 1 instead of 0 to avoid division by 0
        labels_std = exp.targets_df.loc[exp.label_index].std().replace(0, 1)
        labels_mean = exp.targets_df.loc[exp.label_index].mean()

        # Normalize prediction data
        normed_uncertainty = exp.uncertainty / labels_std
        normed_prediction = (clipped_prediction - labels_mean) / labels_std

        # Apply weights to prediction data
        for (target, weight) in zip(exp.target_names, exp.target_weights):
            normed_prediction[target] *= weight
            normed_uncertainty[target] *= weight

        # Normalize feature data
        cls._normalize_data(exp)

        weighted_apriori_values_for_predicted_rows = cls.apply_weights_to_apriori_values(exp)

        # Compute the value of the utility function
        # See slide 43 of the PowerPoint presentation
        # TODO This can probably be turned into a single expression
        # TODO because prediction is written into a new dataframe instead of exp.dataframe, the indices do not match
        #  This leads to nans being inserted and the dimension not working out
        #  For now, work with arrays instead
        # TODO why squeeze?
        if len(exp.target_names) > 1:
            utility = weighted_apriori_values_for_predicted_rows.values.squeeze() + normed_prediction.values.sum(axis=1) +\
                               exp.curiosity * normed_uncertainty.values.sum(axis=1)
        else:
            utility = weighted_apriori_values_for_predicted_rows.values.squeeze() + normed_prediction.values.squeeze() +\
                               exp.curiosity * normed_uncertainty.values.squeeze()

        # TODO This can probably be written into a dataframe
        return utility

    @classmethod
    def compute_novelty_factor(cls, exp):
        features_of_predicted_rows = exp.features_df.iloc[exp.nolabel_index]
        features_of_known_rows = exp.features_df.iloc[exp.label_index]

        distance = distance_matrix(features_of_predicted_rows, features_of_known_rows)
        min_distances = distance.min(axis=1)
        max_of_min_distances = min_distances.max()
        return min_distances * (max_of_min_distances ** (-1))

    @classmethod
    def clip_prediction(cls, exp):
        # TODO how does clip_prediction interact with decide_min_or_max? => move decide max or min into fit function
        clipped_prediction = exp.prediction.copy()
        for (target, max_or_min, threshold) in zip(exp.target_names, exp.target_max_or_min, exp.target_thresholds):
            if max_or_min not in ['min', 'max']:
                raise SequentialLearningException(f'Invalid value for max_or_min, got {max_or_min}')

            if threshold is None:
                continue

            if max_or_min == 'min':
                clipped_prediction[target].clip(lower=threshold, inplace=True)
            elif max_or_min == 'max':
                clipped_prediction[target].clip(upper=threshold, inplace=True)

        return clipped_prediction

    @classmethod
    def _normalize_data(cls, exp):
        # TODO What about categoricals? => double check
        # TODO X nan
        # replace 0s with 1s for division
        # print()
        # print(exp.dataframe[sorted(list(exp.dataframe.columns))].to_string())
        std = exp.dataframe.std().replace(0, 1)
        exp.dataframe = (exp.dataframe - exp.dataframe.mean()) / std
        # print(exp.dataframe[sorted(list(exp.dataframe.columns))].to_string())

    @classmethod
    def apply_weights_to_apriori_values(cls, exp):
        if len(exp.apriori_names) == 0:
            return 0

        apriori_for_predicted_rows = exp.apriori_df.loc[exp.nolabel_index]

        for (col, weight) in zip(exp.apriori_df.columns, exp.apriori_weights):
            apriori_for_predicted_rows[col] *= weight

        # Sum the apriori values row-wise for the case that there are several of them
        # We need to simply add their contributions in that case
        return apriori_for_predicted_rows.sum(axis=1)
