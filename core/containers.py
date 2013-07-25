'''
Created on Jun 14, 2013

@author: jonathanfriedman

TODO:
- transition from fcm data&reader to pandas and Eugene's parser
- add transforms to sample
- implement read_metadata.
'''
from FlowCytometryTools import parse_fcs
from bases import BaseSample, BaseSampleCollection, BasePlate
from GoreUtilities.util import to_list
import graph

class FCSample(BaseSample):
    '''
    A class for holding flow cytometry data from
    a single well or a single tube.
    '''

    @property
    def channels(self):
        '''
        TODO: get the channels from the metadata toavoid having to 
        load the data
        '''
        if self.data is not None:
            return list(self.data.columns)
        else:
            return None

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
        meta = parse_fcs(self.datafile, **kwargs)
        return meta

    def get_meta_fields(self, fields, kwargs={}):
        '''
        TODO: change to extract data from other metadata fields (not just 'text')
        '''
#         if self.data is None:
#             raise Exception, 'Data must be read before extracting metadata.'
        fields = to_list(fields)
        func = lambda x: [x.get_meta()[field] for field in fields]
        kwargs.setdefault('applyto', 'sample')
        return self.apply(func, **kwargs)

    def ID_from_data(self):
        '''
        Returns the well ID from the src keyword in the FCS file. (e.g., A2)
        This keyword may not appear in FCS files generated by other machines,
        in which case this function will raise an exception.
        '''
        try:
            return self.get_metadata('src')[0]
        except:
            raise Exception("The keyword 'src' does not exist in the following FCS file: {}".format(self.datafile))

    def plot(self, channel_names, transform=(None, None), kind='histogram', **kwargs):
        '''
        Plots the flow cytometry data associated with the sample on the current axis.
        Follow with a call to matplotlibs show() in order to see the plot.

        Parameters
        ----------
        FCMdata : fcm data object
        channel_names : str| iterable of str | None
            name (names) channels to plot.
            given a single channel plots a histogram
            given two channels produces a 2d plot

        transform : tuple
            each element is set to None or 'logicle'
            if 'logicle' then channel data is transformed with logicle transformation


        kind : 'scatter', 'histogram'

        Returns
        -------
        None: if no data is loaded
        gHandle: reference to axis


        TODO: fix default value of transform... need cycling function?
        '''
        data = self.get_data()[1] # The index is to keep only the data part (removing the meta data)
        if data is None:
            return None
        else:
            return graph.plotFCM(data, channel_names, transform=transform, kind=kind, **kwargs)

    def view(self, channel_names=None):
        '''
        Loads the current FCS sample viewer

        Parameters
        ----------
        channel_names : str | list of str
            Names of channels to load by default

        Returns
        -------

        Output from sample_viewer
        '''
        from FlowCytometryTools import flowGUI
        return flowGUI.sample_viewer(self.datafile, channel_names=channel_names)

    def transform(self, transform, channels=None, direction='forward',  
                  return_all=True, args=(), **kwargs):
        '''
        Apply transform to specified channels. 
        Return a new sample with transformed data.
        '''
        from transforms import transform_frame
        data = self.get_data()
        tdata = transform_frame(data, transform, channels, direction,
                                           return_all, args, **kwargs)
        tsample = self.copy()
        tsample.set_data(data=tdata)
        return tsample
        

class FCSampleCollection(BaseSampleCollection):
    '''
    A dict-like class for holding flow cytometry samples.
    '''
    _sample_class = FCSample

class FCPlate(BasePlate):
    '''
    A class for holding flow cytometry plate data.
    '''
    _sample_class = FCSample

    def plot(self, channel_names, transform=(None, None), kind='histogram', grid_plot_kwargs={}, **kwargs):
        """
        For details see documentation for FCSample.plot
        Use grid_plot_kwargs to pass keyword arguments to the grid_plot function.
        (For options see grid_plot documentation)


        Returns
        -------
        gHandleList: list
            gHandleList[0] -> reference to main axis
            gHandleList[1] -> a list of lists
                example: gHandleList[1][0][2] returns the subplot in row 0 and column 2
        """
        def plotSampleDataFunction(data):
            """ Function assumes that data is returned as a 2-tuple. The first element is the meta data, the second is the DataFrame """
            return graph.plotFCM(data[1], channel_names, transform=transform, kind=kind, autolabel=False, **kwargs)
        return self.grid_plot(plotSampleDataFunction, **grid_plot_kwargs)

    @property
    def layout(self):
        def data_assigned(well):
            if well.datafile != None:
                return 'Y'
            else:
                return 'N'

        return self.wells.applymap(data_assigned)

if __name__ == '__main__':
    datadir = '../tests/data/'
#     print get_files(datadir)
    plate = FCPlate('test', datadir=datadir, shape=(4,5))
#     print plate
    print plate.wells 
    print plate.well_IDS
    
    plate.apply(lambda x:x.ID, 'ID', applyto='sample', well_ids=['A1','B1'])
    plate.apply(lambda x:x.datafile, 'file', applyto='sample')
    plate.apply(lambda x:x.shape[0], 'counts', keepdata=True)
    plate.get_well_metadata(['date', 'etim'])
    print plate.extracted['file'].values
    
#     plate.wells['1']['A'].get_metadata()
#     
#     well_ids = ['A2' , 'B3']
#     print plate.get_wells(well_ids)
#     
#     plate.clear_well_data()  
#     plate.clear_well_data(well_ids)             
            
        
