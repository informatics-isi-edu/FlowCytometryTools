'''
Created on Jun 14, 2013

@author: jonathanfriedman

TODO:
'''
from FlowCytometryTools import parse_fcs
from bases import Measurement, MeasurementCollection, OrderedCollection, queueable
from GoreUtilities.util import to_list as to_iter
from itertools import cycle
import graph
import inspect
import numpy as np
from FlowCytometryTools.core.transforms import Transformation
from common_doc import doc_replacer
from random import sample

def to_list(obj):
    """ This is a quick fix to make sure indexing of DataFrames
    takes place with lists instead of tuples. """
    obj = to_iter(obj)
    if isinstance(obj, tuple):
        obj = list(obj)
    return obj

class FCMeasurement(Measurement):
    """
    A class for holding flow cytometry data from
    a single well or a single tube.
    """

    @property
    def channels(self):
        """ A DataFrame containing complete channel information """
        if self.meta is not None:
            return self.meta['_channels_']
    @property
    def channel_names(self):
        """ A tuple containing the channel names. """
        if self.meta is not None:
            return self.meta['_channel_names_']

    def read_data(self, **kwargs):
        '''
        Read the datafile specified in Sample.datafile and
        return the resulting object.
        Does NOT assign the data to self.data
        '''
        meta, data = parse_fcs(self.datafile, **kwargs)
        return data

    def read_meta(self, **kwargs):
        '''
        '''
        kwargs['meta_data_only'] = True
        kwargs['reformat_meta'] = True
        meta = parse_fcs(self.datafile, **kwargs)
        return meta

    def get_meta_fields(self, fields, kwargs={}):
        '''
        Return a dictionary of metadata fields
        '''
        fields = to_list(fields)
        meta = self.get_meta()
        return dict( ((field, meta.get(field)) for field in fields ) )

    def ID_from_data(self, ID_field='$SRC'):
        '''
        Returns the well ID from the src keyword in the FCS file. (e.g., A2)
        This keyword may not appear in FCS files generated by other machines,
        in which case this function will raise an exception.
        '''
        try:
            return self.get_meta_fields(ID_field)[0]
        except:
            raise Exception("The keyword '{}' does not exist in the following FCS file: {}".format(ID_field, self.datafile))

    @doc_replacer
    def plot(self, channel_names, transform=(None, None), kind='histogram',
             gates=None, transform_first=True, apply_gates=True, plot_gates=True,
             gate_colors=None, **kwargs):
        """
        Plots the flow cytometry data associated with the sample on the current axis.

        To produce the plot, follow up with a call to matplotlib's show() function.

        Parameters
        ----------
        {graph_plotFCM_pars}
        {FCMeasurement_plot_pars}
        {common_plot_ax}
        gates : [None, Gate, list of Gate]
            Gate must be of type {_gate_available_classes}.
        kwargs : dict
            Additional keyword arguments to be passed to graph.plotFCM

        Returns
        -------
        None : if no data is present
        plot_output : output of plot command used to draw (e.g., output of hist)

        Examples
        ----------
        >>> sample.plot('Y2-A', bins=100, alpha=0.7, color='green', normed=1) # 1d histogram
        >>> sample.plot(['B1-A', 'Y2-A'], cmap=cm.Oranges, colorbar=False) # 2d histogram
        """
#         data = self.get_data() # The index is to keep only the data part (removing the meta data)
        # Transform sample

        def _trans(sample, channel_names, transformList):
            for c,t in zip(channel_names, transformList):
                if t is not None:
                    sample = sample.transform(t, channels=c)
                else:
                    pass
            return sample

        def _gates(sample, gates):
            if gates is None:
                return sample
            for gate in gates:
                sample = sample.gate(gate)
            return sample

        ax = kwargs.get('ax')

        channel_names = to_list(channel_names)
        transformList = to_list(transform)
        gates         = to_list(gates)

        if len(transformList) == 1:
             transformList *= len(channel_names)

        sample_tmp = self.copy()
        if apply_gates:
            if transform_first:
                sample_tmp = _trans(sample_tmp, channel_names, transformList)
                sample_tmp = _gates(sample_tmp, gates)
            else:
                sample_tmp = _gates(sample_tmp, gates)
                sample_tmp = _trans(sample_tmp, channel_names, transformList)
        else:
            sample_tmp = _trans(sample_tmp, channel_names, transformList)

        data = sample_tmp.get_data()
        plot_output  = graph.plotFCM(data, channel_names, kind=kind, **kwargs)

        if plot_gates and gates is not None:
            if gate_colors is None:
                gate_colors = cycle(('b', 'g', 'r', 'm', 'c', 'y'))
            for (g,c) in zip(gates, gate_colors):
                g.plot(ax=ax, ax_channels=channel_names, color=c)

        return plot_output

    def view(self):
        '''
        Loads the current FCS sample viewer

        Parameters
        ----------
        channel_names : str | list of str
            (Not implemented yet)
            Names of channels to load by default

        Returns
        -------

        TODO: Implement channel_names
        '''
        #if launch_new_subprocess: # This is not finished until I can list the gates somewhere
            #from FlowCytometryTools import __path__ as p
            #from subprocess import call
            #import os
            #script_path = os.path.join(p[0], 'GUI', 'flomeasurementwGUI.py')
            #call(["python", script_path, self.datafile])
        #else:
        from FlowCytometryTools.GUI import gui
        return gui.FCGUI(measurement=self)
    
    @queueable
    @doc_replacer
    def transform(self, transform, direction='forward',
                  channels=None, return_all=True, auto_range=True,
                  use_spln=True, get_transformer=False, ID = None,
                  apply_now=True,
                  args=(), **kwargs):
        """
        Applies a transformation to the specified channels.

        The transformation parameters are shared between all transformed channels.
        If different parameters need to be applied to different channels, use several calls to `transform`.

        Parameters
        ------------
        {FCMeasurement_transform_pars}
        ID : hashable | None
            ID for the resulting collection. If None is passed, the original ID is used.

        Returns
        -------
        new : FCMeasurement
            New measurement containing the transformed data.
        transformer : Transformation
            The Transformation applied to the input measurement.
            Only returned if get_transformer=True.

        Examples
        --------
        {FCMeasurement_transform_examples}
        """
        data = self.get_data()

        channels = to_list(channels)
        if channels is None:
            channels = data.columns
        ## create transformer
        if isinstance(transform, Transformation):
            transformer = transform
        else: 
            if auto_range: #determine transformation range
                if 'd' in kwargs:
                    warnings.warn('Encountered both auto_range=True and user-specified range value in parameter d.\n Range value specified in parameter d is used.')
                else:
                    channel_meta = self.channels
                    # the -1 below because the channel numbers begin from 1 instead of 0 (this is fragile code)
                    ranges = [float(r['$PnR']) for i, r in channel_meta.iterrows() if self.channel_names[i-1] in channels]
                    if not np.allclose(ranges, ranges[0]):
                        raise Exception, 'Not all specified channels have the same data range, therefore they cannot be transformed together.'
                    kwargs['d'] = np.log10(ranges[0])
            transformer = Transformation(transform, direction, args, **kwargs)        
        ## create new data
        transformed = transformer(data[channels], use_spln)   
        if return_all:
            new_data = data
        else:
            new_data = data.filter(columns)
        new_data[channels] = transformed
        ## create new Measurement
        new = self.copy()    
        new.data = new_data
        
        if ID is not None:
            new.ID = ID
        if get_transformer:
            return new, transformer
        else:
            return new

    @doc_replacer
    def subsample(self, key, order='random', auto_resize=False):
        """
        Allows arbitrary slicing (subsampling) of the data.

        Parameters
        ---------------
        {FCMeasurement_subsample_parameters}

        Returns
        -------------
        new sample with subsampled event data.
        """
        data = self.get_data()
        num_events = data.shape[0]

        if isinstance(key, float):
            if (key > 1.0) or (key < 0.0):
                raise ValueError('If float, key must be between 0.0 and 1.0')
            key = int(num_events*key)
        elif isinstance(key, tuple):
            all_float = all([isinstance(x, float) for x in key])
            if (len(key) > 2) or (not all_float):
                raise ValueError('Tuple must consist of two floats, each between 0.0 and 1.0')
            start = int(num_events * key[0])
            stop  = int(num_events * key[1])
            key = slice(start, stop) # Convert to a slice

        try:
            if isinstance(key, slice):
                if auto_resize:
                    stop = key.stop if key.stop < num_events else num_events
                    start = key.start if key.start < num_events else num_events
                    key = slice(start, stop, key.step) # Generate new slice
                newdata = data.iloc[key]
            elif isinstance(key, int):
                if auto_resize:
                    if key > num_events:
                        key = num_events
                if key < 1:
                    # EDGE CAES: Must return an empty sample
                    order = 'start'
                if order == 'random':
                    newdata = data.loc[sample(data.index, key)] # Use loc not iloc here!!
                elif order == 'start':
                    newdata = data.iloc[:key]
                elif order == 'end':
                    newdata = data.iloc[-key:]
                else:
                    raise ValueError("order must be in ('random', 'start', 'end')")
            else:
                raise TypeError("'key' must be of type int, float, tuple or slice.")
        except IndexError:
            print("If you're encountering an out-of-bounds error, try to setting 'auto_resize' to True.")
            raise
        newsample = self.copy()
        newsample.set_data(data=newdata)
        return newsample

    @queueable
    @doc_replacer
    def gate(self, gate, apply_now=True):
        '''
        Apply given gate and return new gated sample (with assigned data).

        Parameters
        ---------------

        gate : {_gate_available_classes}
        '''
        data = self.get_data()
        newdata = gate(data)
        newsample = self.copy()
        newsample.data = newdata
        return newsample

    @property
    def counts(self):
        """ Returns total number of events. """
        data = self.get_data()
        return data.shape[0]

class FCCollection(MeasurementCollection):
    '''
    A dict-like class for holding flow cytometry samples.
    '''
    _measurement_class = FCMeasurement

    @doc_replacer
    def transform(self, transform, direction='forward', share_transform=True,
                  channels=None, return_all=True, auto_range=True,
                  use_spln=True, get_transformer=False, ID = None,
                  apply_now=True,
                  args=(), **kwargs):
        '''
        Apply transform to each Measurement in the Collection.

        Return a new Collection with transformed data.

        {_containers_held_in_memory_warning}

        Parameters
        ----------
        {FCMeasurement_transform_pars}
        ID : hashable | None
            ID for the resulting collection. If None is passed, the original ID is used.

        Returns
        -------
        new : FCCollection
            New collection containing the transformed measurements.
        transformer : Transformation
            The Transformation applied to the measurements.
            Only returned if get_transformer=True & share_transform=True.

        Examples
        --------
        {FCMeasurement_transform_examples}
        '''
        new = self.copy()
        if share_transform:
            channel_meta  = self.values()[0].channels
            channel_names = self.values()[0].channel_names
            if channels is None:
                channels = list(channel_names)
            else:
                channels = to_list(channels)
            ## create transformer
            if isinstance(transform, Transformation):
                transformer = transform
            else:
                if auto_range: #determine transformation range
                    if 'd' in kwargs:
                        warnings.warn('Encountered both auto_range=True and user-specified range value in parameter d.\n Range value specified in parameter d is used.')
                    else:
                        # the -1 below because the channel numbers begin from 1 instead of 0 (this is fragile code)
                        ranges = [float(r['$PnR']) for i, r in channel_meta.iterrows() if channel_names[i-1] in channels]

                        if not np.allclose(ranges, ranges[0]):
                            raise Exception, 'Not all specified channels have the same data range, therefore they cannot be transformed together.'
                        kwargs['d'] = np.log10(ranges[0])
                transformer = Transformation(transform, direction, args, **kwargs)
                if use_spln:
                    xmax = self.apply(lambda x:x[channels].max().max(), applyto='data').max().max()
                    xmin = self.apply(lambda x:x[channels].min().min(), applyto='data').min().min()
                    transformer.set_spline(xmin, xmax)
            ## transform all measurements     
            for k,v in new.iteritems(): 
                new[k] = v.transform(transformer, channels=channels, return_all=return_all, use_spln=use_spln, apply_now=apply_now)
        else:
            for k,v in new.iteritems(): 
                new[k] = v.transform(transform, direction=direction, channels=channels, 
                                     return_all=return_all, auto_range=auto_range, get_transformer=False,
                                     use_spln=use_spln, apply_now=apply_now, args=args, **kwargs)
        if ID is not None:
            new.ID = ID
        if share_transform and get_transformer:
            return new, transformer
        else:
            return new

    @doc_replacer
    def gate(self, gate, ID=None, apply_now=True):
        '''
        Applies the gate to each Measurement in the Collection, returning a new Collection with gated data.

        {_containers_held_in_memory_warning}

        Parameters
        ------------------

        gate : {_gate_available_classes}

        ID : [ str, numeric, None]
            New ID to be given to the output. If None, the ID of the current collection will be used.
        '''
        def func(well):
            return well.gate(gate, apply_now=apply_now)
        return self.apply(func, output_format='collection', ID=ID)

    @doc_replacer
    def subsample(self, key, order='random', auto_resize=False, ID=None):
        """
        Allows arbitrary slicing (subsampling) of the data.

        Note: when using order='random', the sampling is random
        for each of the measurements in the collection.

        Parameters
        ---------------
        {FCMeasurement_subsample_parameters}

        Returns
        -------------
        new collection of subsampled event data.
        """
        def func(well):
            return well.subsample(key=key, order=order, auto_resize=auto_resize)
        return self.apply(func, output_format='collection', ID=ID)

    def counts(self, ids=None, setdata=False, output_format='DataFrame'):
        """
        Return the counts in each of the specified measurements.

        Parameters
        ----------
        ids : [hashable | iterable of hashables | None]
            Keys of measurements to get counts of.
            If None is given get counts of all measurements.
        setdata : bool
            Whether to set the data in the Measurement object.
            Used only if data is not already set.
        output_format : DataFrame | dict
            Specifies the output format for that data.

        Returns
        -------
        DataFrame/Dictionary keyed by measurement keys containing the corresponding counts.
        """
        return self.apply(lambda x:x.counts, ids=ids, setdata=setdata, output_format=output_format)


class FCOrderedCollection(OrderedCollection, FCCollection):
    '''
    A dict-like class for holding flow cytometry samples that are arranged in a matrix.
    '''

    @doc_replacer
    def plot(self, channel_names,  kind='histogram', transform=(None, None),
             gates=None, transform_first=True, apply_gates=True, plot_gates=True, gate_colors=None,
             ids=None, row_labels=None, col_labels=None,
             xlim=None, ylim=None,
             autolabel=True,
             **kwargs):
        """
        Produces a grid plot with each subplot corresponding to the data at the given position.

        Parameters
        ---------------
        {FCMeasurement_plot_pars}
        {graph_plotFCM_pars}

        Layout
        ========================
        {_graph_grid_layout}

        Returns
        -------
        {_graph_grid_layout_returns}

        Examples
        ------------
        Below, plate is an instance of the FCOrderedCollection

        >>> plate.plot(['SSC-A', 'FSC-A'], kind='histogram', transform='hlog', autolabel=True)
        >>> plate.plot(['SSC-A', 'FSC-A'], transform='hlog', xlim=(0, 10000))
        >>> plate.plot(['B1-A', 'Y2-A'], transform='hlog', kind='scatter', color='red', s=1, alpha=0.3)

        .. note:

            For more details see documentation for FCMeasurement.plot
            **kwargs passes arguments to both grid_plot and to FCMeasurement.plot.
        """
        ##
        # Note
        # -------
        # The function assumes that grid_plot and FCMeasurement.plot use unique key words.
        # Any key word arguments that appear in both functions are passed only to grid_plot in the end.

        ##
        # Automatically figure out which of the kwargs should
        # be sent to grid_plot instead of two sample.plot
        # (May not be a robust solution, we'll see as the code evolves

        grid_arg_list = inspect.getargspec(OrderedCollection.grid_plot).args

        grid_plot_kwargs = { 'ids' :  ids,
                             'row_labels' :  row_labels,
                             'col_labels' :  col_labels}

        for key, value in kwargs.items():
            if key in grid_arg_list:
                kwargs.pop(key)
                grid_plot_kwargs[key] = value

        ##########
        # Defining the plotting function that will be used.
        # At the moment grid_plot handles the labeling 
        # (rather than sample.plot or the base function
        # in GoreUtilities.graph

        def plot_sample(sample, ax):
            return sample.plot(channel_names, transform=transform, ax=ax,
                               gates=gates, transform_first=transform_first, apply_gates=apply_gates, 
                               plot_gates=plot_gates, gate_colors=gate_colors,
                               colorbar=False,
                               kind=kind, autolabel=False, **kwargs)

        xlabel, ylabel = None, None

        if autolabel:
            cnames = to_list(channel_names)
            xlabel = cnames[0]
            if len(cnames) == 2:
                ylabel = cnames[1]

        return self.grid_plot(plot_sample, xlim=xlim, ylim=ylim,
                    xlabel=xlabel, ylabel=ylabel,
                    **grid_plot_kwargs)

FCPlate = FCOrderedCollection

if __name__ == '__main__':
    #print FCMeasurement.plot.__doc__
#     print FCOrderedCollection.plot.__doc__
    #print FCMeasurement.transform.__doc__
    #print FCOrderedCollection.transform.__doc__
    
#     from datetime import date, timedelta
#     from numpy import array
#     t1 = date(2014,3,15)
#      
#     flow_plates = []
#     for i in range(3):
#         t = t1 + timedelta(days=i)
#         datadir = '/home/yonatanf/Dropbox/Gore/invasion/fc_data/%s/EXP_32/'%t.isoformat()
#         flow_plates.append(FCPlate.from_dir('t%d'%(i+1), datadir, parser='name', pattern='*EXP_32*.fcs').dropna())
#  
#     hplates = [p.transform('hlog', apply_now=False, channels=['FSC-A','SSC-A','B1-A'], b=2.5) for p in flow_plates]    
#     print hplates[-1].counts()
#     
#     from FlowCytometryTools import PolyGate
#     size_gate = PolyGate([(8.530e+02, 1.593e+03), (1.419e+03, 1.306e+02), (8.429e+03, 4.299e+03), (6.051e+03, 5.966e+03)], ('FSC-A', 'SSC-A'), region='in', name='gate1')
#     yfp_gate = PolyGate([(4.960e+03, 6.597e+02), (1.104e+03, 7.098e+02), (5.613e+03, 8.293e+03), (8.973e+03, 6.732e+03)], ('B1-A', 'FSC-A'), region='in', name='gate2')
# 
#     gated_size = [hplate.gate(size_gate, apply_now=False) for hplate in hplates]
#     size_counts = array([gs.counts().values for gs in gated_size])

    import glob
    datadir = '../tests/data/Plate01/'
    fname = glob.glob(datadir + '*.fcs')[0]
    sample = FCMeasurement(1, datafile=fname)
     
    from FlowCytometryTools import ThresholdGate
    g = ThresholdGate(6e3, 'FSC-A', 'above')
 
    plate = FCPlate.from_dir('p', datadir).dropna()
    print plate.counts()
     
    queued = plate.transform('hlog', apply_now=False).gate(g, apply_now=False)
    print queued.counts()
    print type(queued['A4']._data)
     
    in_mem = plate.transform('hlog', apply_now=True).gate(g, apply_now=True)
    print in_mem.counts()
    print type(in_mem['A4']._data)
#
    #import time
    #s = time.clock()
    #hplate = plate.transform('hlog', channels=['FSC-A', 'SSC-A'], use_spln=False)
    #e = time.clock()
    #
    #ss = time.clock()
    #hplate = plate.transform('hlog', channels=['FSC-A', 'SSC-A'])
    #es = time.clock()
    #print e-s, es-ss
    #print plate.wells 
    #print plate.well_IDS
    #plate.apply(lambda x:x.ID, 'ID', applyto='sample', well_ids=['A1','B1'])
    #plate.apply(lambda x:x.datafile, 'file', applyto='sample')
    #plate.apply(lambda x:x.shape[0], 'counts', keepdata=True)
    #plate.get_well_metadata(['date', 'etim'])
    #print plate.extracted['file'].values
#     plate.wells['1']['A'].get_metadata()
#     
#     well_ids = ['A2' , 'B3']
#     print plate.get_wells(well_ids)
#     
#     plate.clear_well_data()  
#     plate.clear_well_data(well_ids)             
