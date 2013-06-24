#!/usr/bin/env python
"""
Modules contains graphing routines common for flow cytometry files.
"""
from fcm.graphics.util import bilinear_interpolate
from bases import to_list
import numpy
import pylab as pl
import matplotlib

def plot_histogram2d(x, y, bins=200, ax=None, **kwargs):
    '''
    Plots a 2D histogram given x, y and number of bins
    Parameters
    ----------
    x
    y
    bins
    ax
    norm
    '''
    if ax == None:
        ax = pl.gca()

    kwargs.setdefault('cmap', pl.cm.Reds)
    kwargs.setdefault('norm', matplotlib.colors.LogNorm())

    # Estimate the 2D histogram
    counts_hist, xedges, yedges = numpy.histogram2d(x, y, bins=bins)
    # counts_hist needs to be rotated and flipped
    counts_hist = numpy.rot90(counts_hist)
    counts_hist = numpy.flipud(counts_hist)
    # Mask zeros with a value of 0
    masked_hist = numpy.ma.masked_where(counts_hist == 0, counts_hist)
    return ax.pcolormesh(xedges, yedges, masked_hist, **kwargs)

def pseudocolor_bilinear_interpolate(x, y, edgecolors='none', ax=None, **kwargs):
    '''
    Pseudocolor plot based on FCMs bilinear interpolate function.
    '''
    if ax == None: ax = pl.gca()

    # Set pretty defaults for plotting
    kwargs.setdefault('s', 1)
    z = bilinear_interpolate(x, y)
    return ax.scatter(x, y, c=z, s=s, edgecolors=edgecolors, **kwargs)

def plotFCM(data, channel_names, transform=(None, None), plot2d_type='dot2d', ax=None, **kwargs):
    '''
    Plots the sample on the current axis.
    Follow with a call to matplotlibs show() in order to see the plot.

    Parameters
    ----------
    FCMdata : fcm data object
    channel_names : str| iterable of str
        name (names) channels to plot.
        given a single channel plots a histogram
        given two channels produces a 2d plot

    transform : tuple
        each element is set to None or 'logicle'
        if 'logicle' then channel data is transformed with logicle transformation

    plot2d_type : 'dot2d', 'hist2d', 'pseudo with bilinear'

    ax : reference | None
        specifies which axis to plot on

    Returns
    -------
    pHandle: reference to plot
    '''
    if ax == None: ax = pl.gca()

    # Find indexes of the channels
    channel_names = to_list(channel_names)
    channelIndexList = [data.name_to_index(channel) for channel in channel_names]

    # Transform data
    transformList = to_list(transform)

    for channel, transformType in zip(channelIndexList, transformList):
        if transformType == 'logicle':
            data.logicle(channels=[channel])

    if len(channelIndexList) == 1:
        # 1d so histogram plot
        ch1i = channelIndexList[0]
        pHandle = ax.hist(data[:, ch1i], **kwargs)

    elif len(channelIndexList) == 2:
        x = data[:, channelIndexList[0]] # index of first channels name
        y = data[:, channelIndexList[1]] # index of seconds channels name

        if plot2d_type == 'dot2d':
            pHandle = ax.scatter(x, y, **kwargs)
        elif plot2d_type == 'hist2d':
            pHandle = plot_histogram2d(x, y, ax=ax, **kwargs)
        elif plot2d_type == 'pseudo with bilinear':
            pHandle = pseudocolor_bilinear_interpolate(x, y, ax=ax, **kwargs)
        else:
            raise Exception('Not a valid plot type')

    return pHandle


def plot_gate(gate_type, channel_names, coordinates, gate_name=None):
    '''
    TODO: Implement
    Plots a gate on the current axis.

    Parameters
    ----------
    gate_type : 'quad', 'polygon', 'interval', 'threshold'
        specifies the shape of the gate
    channel_names : str | iterable of str
        name (names) channels to plot.
        given a single channel plots a histogram
        given two channels produces a 2d plot
    coordinates : tuple
        For:
            'quad'     gate : a tuple of two numbers (x, y)
            'polygon'  gate : a tuple of 3 or more 2d coordinates ((x1, y1), (x2, y2), (x3, y3), ...)
            'interval' gate : a tuple of (channel_name, x1 or y1, x2 or y2) ?? Still need to specify channel names

    transform : tuple
        each element is set to None or 'logicle'
        if 'logicle' then channel data is transformed with logicle transformation

    gate_name : str | None
        Not supported yet

    Returns
    -------
    reference to plot
    '''
    pass

def plot_quad_gate(x, y, *args, **kwargs):
    ''' 
    Plots a quad gate.
    vertical line at x
    horizontal line at y
    '''
    pl.axvline(x, *args, **kwargs)
    pl.axhline(y, *args, **kwargs)