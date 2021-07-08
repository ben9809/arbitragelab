# Copyright 2019, Hudson and Thames Quantitative Research
# All rights reserved
# Read more: https://hudson-and-thames-arbitragelab.readthedocs-hosted.com/en/latest/additional_information/license.html

# pylint: disable=missing-module-docstring, invalid-name
import warnings
import numpy as np
import pandas as pd
from typing import Union, Callable
from scipy import optimize, special
from mpmath import nsum, inf, gamma, digamma, fac
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from arbitragelab.time_series_approach.ou_optimal_threshold import OUModelOptimalThreshold
from arbitragelab.util import devadarsh


class OUModelOptimalThresholdBertram(OUModelOptimalThreshold):
    """
    This class implements the analytic solutions of the optimal trading thresholds for the series
    with mean-reverting properties. The methods are described in the following publication:
    Bertram, W. K. (2010). Analytic solutions for optimal statistical arbitrage trading.
    Physica A: Statistical Mechanics and its Applications, 389(11):2234–2243.
    Link: http://www.stagirit.org/sites/default/files/articles/a_0340_ssrn-id1505073.pdf

    Assumptions of the method:
    1. The series Xt = ln(Pt) follows a Ornstein-Uhlenbeck process, where Pt is a price series of a asset or a spread.
    2. A Trading strategy is defined by entering a trade when Xt = a, exiting the trade at Xt = m,
       and waiting until the process returns to Xt = a, to complete the trading cycle.
    3. a < m
    """

    def __init__(self):
        """
        Initializes the module parameters.
        """

        super().__init__()

        # devadarsh.track('OUModelOptimalThresholdBertram')

    def expected_trade_length(self, a: float, m: float):
        """
        Calculates equation (9) in the paper to get the expected trade length.

        :param a: (float) The entry threshold of the trading strategy
        :param m: (float) The exit threshold of the trading strategy
        :return: (float) The expected trade length of the trading strategy
        """

        return (np.pi / self.mu) * (self._erfi_scaler(m) - self._erfi_scaler(a))

    def trade_length_variance(self, a: float, m: float):
        """
        Calculates equation (10) in the paper to get the variance of trade length.

        :param a: (float) The entry threshold of the trading strategy
        :param m: (float) The exit threshold of the trading strategy
        :return: (float) The variance of trade length of the trading strategy
        """

        const_1 = (m - self.theta) * np.sqrt(2 * self.mu) / self.sigma
        const_2 = (a - self.theta) * np.sqrt(2 * self.mu) / self.sigma

        term_1 = self._w1(const_1) - self._w1(const_2) - self._w2(const_1) + self._w2(const_2)
        term_2 = (self.mu)**2 

        return term_1 / term_2

    def expected_return(self, a: float, m: float, c: float):
        """
        Calculates equation (5) in the paper to get the expected return.

        :param a: (float) The entry threshold of the trading strategy
        :param m: (float) The exit threshold of the trading strategy
        :param c: (float) The transaction costs of the trading strategy
        :return: (float) The expected return of the trading strategy
        """

        return (m - a - c) / self.expected_trade_length(a, m)

    def return_variance(self, a: float, m: float, c: float):
        """
        Calculates equation (6) in the paper to get the variance of return.

        :param a: (float) The entry threshold of the trading strategy
        :param m: (float) The exit threshold of the trading strategy
        :param c: (float) The transaction costs of the trading strategy
        :return: (float) The variance of return of the trading strategy
        """

        return (m - a - c)**2 * self.trade_length_variance(a, m) / (self.expected_trade_length(a, m) ** 3)

    def sharpe_ratio(self, a: float, m: float, c: float, rf: float):
        """
        Calculates equation (15) in the paper to get the Sharpe ratio.

        :param a: (float) The entry threshold of the trading strategy
        :param m: (float) The exit threshold of the trading strategy
        :param c: (float) The transaction costs of the trading strategy
        :param rf: (float) The risk free rate
        :return: (float) The Sharpe ratio of the strategy
        """

        r = rf / self.expected_trade_length(a, m)

        return (self.expected_return(a, m, c) - r) / np.sqrt(self.return_variance(a, m ,c))



    def get_threshold_by_maximize_expected_return(self, c: float):
        """
        Solves equation (13) in the paper to get the optimal trading thresholds.

        :param c: (float) The transaction costs of the trading strategy
        :return: (tuple) The value of the optimal trading thresholds
        """

        # equation (13) in the paper
        equation = lambda a: np.exp(self.mu * ((a - self.theta) ** 2) / (self.sigma ** 2)) * (2 * (a - self.theta) + c) - self.sigma * np.sqrt(np.pi / self.mu) * self._erfi_scaler(a)
        
        initial_guess = self.theta - c - 1e-2 
        root = optimize.fsolve(equation, initial_guess)[0]

        return root, 2 * self.theta - root

    def get_threshold_by_maximize_sharpe_ratio(self, c: float, rf: float):
        """
        Minimize -1 * Sharpe ratio to get the optimal trading thresholds.

        :param c: (float) The transaction costs of the trading strategy
        :param rf: (float) The risk free rate
        :return: (tuple) The value of the optimal trading thresholds
        """
        
        negative_sharpe_ratio = lambda a: -1 * self.sharpe_ratio(a, 2 * self.theta - a, c, rf)
        negative_sharpe_ratio = np.vectorize(negative_sharpe_ratio)

        initial_guess = self.theta - rf - c
        sol = optimize.minimize(negative_sharpe_ratio, initial_guess, method="Nelder-Mead").x[0]

        return sol, 2 * self.theta - sol

    def _erfi_scaler(self, const: float):
        """
        A helper function for simplifing equation expression

        :param const: (float) The input value of the function
        :return: (float) The output value of the function
        """

        return special.erfi((const - self.theta) * np.sqrt(self.mu) / self.sigma)

    def _w1(self, const: float):
        """
        A helper function for simplifing equation expression

        :param const: (float) The input value of the function
        :return: (float) The output value of the function
        """

        common_term = lambda k: gamma(k / 2) * ((1.414 * const) ** k) / fac(k)
        term_1 = (nsum(common_term, [1, inf]) / 2) ** 2
        term_2 = (nsum(lambda k: common_term(k) * ((-1) ** k), [1, inf]) / 2) ** 2
        w1 = term_1 - term_2

        return float(w1)

    def _w2(self, const: float):
        """
        A helper function for simplifing equation expression

        :param const: (float) The input value of the function
        :return: (float) The output value of the function
        """

        middle_term = lambda k: (digamma((2 * k - 1) / 2) - digamma(1)) * gamma((2 * k - 1) / 2) * ((1.414 * const) ** (2 * k - 1)) / fac((2 * k - 1))
        w2 = nsum(middle_term, [1, inf])

        return float(w2)

    def plot_optimal_trading_thresholds_c(self, c_list: list):
        """
        Calculates optimal trading thresholds by maximizing expected return and plots optimal trading thresholds versus transaction costs.

        :param c_list: (list) A list contains transaction costs
        :return: (plt.Figure) Figure that plots optimal trading thresholds versus transaction costs
        """

        a_list = []
        for c in c_list:
            a, m = self.get_threshold_by_maximize_expected_return(c)
            a_list.append(a)

        fig = plt.figure()
        plt.plot(c_list, a_list)
        plt.title("Optimal Trade Entry vs Trans. Costs")  # title
        plt.ylabel("a")  # y label
        plt.xlabel("c")  # x label

        return fig

    def plot_maximum_expected_return(self, c_list: list):
        """
        Plots maximum expected returns versus transaction costs.

        :param c_list: (list) A list contains transaction costs
        :return: (plt.Figure) Figure that plots maximum expected returns versus transaction costs
        """

        a_list = []
        m_list = []
        for c in c_list:
            a, m = self.get_threshold_by_maximize_expected_return(c)
            a_list.append(a)
            m_list.append(m)

        func = np.vectorize(self.expected_return)

        fig = plt.figure()
        plt.plot(c_list, func(a_list, m_list, c_list))
        plt.title("Max E[Return] vs Trans. Costs")  # title
        plt.ylabel(r'${\mu}^* (a, c)$')  # y label
        plt.xlabel("c")  # x label

        return fig

    def plot_optimal_trading_thresholds_rf(self, c: float, rf_list: list):
        """
        Calculates optimal trading thresholds by maximizing Sharpe ratio and plots optimal trading thresholds versus risk free rates.

        :param c: (float) The transaction costs of the trading strategy
        :param rf_list: (list) A list contains risk free rates
        :return: (plt.Figure) Figure that plots optimal trading thresholds versus risk free rates
        """

        a_list = []
        for rf in rf_list:
            a, m = self.get_threshold_by_maximize_sharpe_ratio(c, rf)
            a_list.append(a)

        fig = plt.figure()
        plt.plot(rf_list, a_list)
        plt.title("Optimal Trade Entry vs Risk−free Rate")  # title
        plt.ylabel("a")  # y label
        plt.xlabel("rf")  # x label

        return fig

    def plot_maximum_sharpe_ratio(self, c: float, rf_list: list):
        """
        Plots maximum Sharpe ratios versus risk free rates.

        :param c: (float) The transaction costs of the trading strategy
        :param rf_list: (list) A list contains risk free rates
        :return: (plt.Figure) Figure that plots maximum Sharpe ratios versus risk free rates
        """

        s_list = []
        for rf in rf_list:
            a, m = self.get_threshold_by_maximize_sharpe_ratio(c, rf)
            s_list.append(self.sharpe_ratio(a, m, c, rf))

        fig = plt.figure()
        plt.plot(rf_list, s_list)
        plt.title("Max Sharpe Ratio vs Risk−free Rate")  # title
        plt.ylabel("r'$S^* (a, c, r)$'")  # y label
        plt.xlabel("rf")  # x label

        return fig




