#!/usr/bin/env python
import pylab as pl
import util
from matplotlib.widgets import Button, Cursor
from matplotlib.collections import RegularPolyCollection
from matplotlib.nxutils import points_inside_poly
from matplotlib.colors import colorConverter
from utilities import dialogs
import numpy
from fcm import loadFCS
from FlowCytometryTools import plotFCM

##
# TODO: channel_list should be names rather than channel numbers
## 

def euclid_distance((x1, y1), (x2, y2)):
    return numpy.sqrt((x1-x2)**2 + (y1 - y2)**2)

###################
# DEFINITIONS 
###################

class MOUSE:
    leftClick = 1
    rightClick = 3

class STYLE:
    InactivePolygonGate = {'color' : 'black', 'linestyle' : 'solid', 'fill' : False}
    ActivePolygonGate = {'color' : 'red', 'fill' : False}

    #SuggestToActivateGate = {'color' : 'red', 'fill' : 'gray', 'alpha' : 0.4}
    TemporaryPolygonGateBorderLine = {'color' : 'black'}
    PolygonGateBorderLine = {'color' : 'None',  'linestyle' : 'None', 'marker':'s', 'mfc':'r', 'alpha':0.6}

    InactiveQuadGate = {'color' : 'black', 'linewidth' : 1}
    ActiveQuadGate   = {'color' : 'red', 'linewidth' : 2}
    InactiveQuadGateCenter = {'color' : 'black', 'marker' : 's', 'markersize' : 8}
    ActiveQuadGateCenter   = {'color' : 'red', 'marker' : 's', 'markersize' : 8}

    DATUM_IN_COLOR = colorConverter.to_rgba('red')
    DATUM_OUT_COLOR = colorConverter.to_rgba('gray')

class STATE_GK:
    START_DRAWING = 'Start Drawing Gate'
    START_DRAWING_QUAD_GATE = 'Start Drawing Quad Gate'
    KEEP_DRAWING = 'Creating a gate'
    WAITING = 'Waiting'
    QUIT = 'Quitting'
    DELETE_GATE = 'Delete Active Gate'

class Filter(object):
    """An object representing a gatable region"""

    def __init__(self, vert=None, channels=None, name=None, gateKeeper=None):
        """
        vert = vertices of gating region
        channels = indices of channels to gate on.
        """
        self.attributeList = ['cidpress', 'cidrelease', 'cidmotion', 'cidpick', 'cidkey']
        self.set_state('Active')

        for attribute in self.attributeList:
            setattr(self, attribute, None)

        self.vert = vert
        self.channels = list(channels)
        self.press = None
        self.active = False

        if name is None:
            self.name = "Unnamed Gate"
        else:
            self.name = name

        self.gateKeeper = gateKeeper
        ### Used while drawing the gate ###

        ### Used for GUI ###
        self.fig = gateKeeper.fig
        self.ax = gateKeeper.ax
        self.connect()
        print 'Just created a new gate: ' + str(self)

    #def __repr__(self):
        #return "{} ({}, {}, {})".format(self.__class__, self.vert, self.channels, self.name)


    def __repr__(self):
        return "{} ({}, {}, {}, {})".format(self.__class__, self.vert, self.channels, self.name, self.state)

    #def __str__(self):
        #return "<{} ({}) on {}>".format(self.__class__, self.name, self.channels)

    # Used for debugging
    def __str__(self):
        return "<{} ({}) on {} state {}>".format(self.__class__, self.name, self.channels, self.state)

    def set_state(self, state):
        self.state = state

    def is_active(self):
        return self.state == 'Active'


    #################
    ## GUI Control 
    #################

    def disconnect(self):
        """ disconnects all the stored connection ids """
        for attribute in self.attributeList:
            cid = getattr(self, attribute)
            if cid is not None:
                self.fig.canvas.mpl_disconnect(cid)

    def on_mouse_motion(self, event):
        print 'on_mouse_motion: not defined'

    def on_release(self, event):
        'on release we reset the press data'
        print 'on_release: not defined'

    def on_mouse_pick(self, event):
        util.raiseNotDefined()

    def on_press(self, event):
        print 'on_press: not defined'

    def on_keyboard_press(self, event):
        print 'on_keyboard_press: not defined'

    def get_control_artist(self):
        util.raiseNotDefined('The control artist has not been defined for the given gate.')

    def get_gate_artists(self):
        '''
        Returns a list of all the graphical components that make up a gate.
        '''
        return self.artistList

    def contains(self, event):
        if self.channels != self.gateKeeper.current_channels:
            return False
        contains, attrd = self.get_control_artist().contains(event)
        return contains


    def set_visible(self, visible=True):
        '''
        Method is responsible for showing or hiding the gate.
        Useful when the x/y axis change.
        '''
        for artist in self.artistList:
            artist.set_visible(visible)

        if visible:
            if self.state == 'Active':
                self.activate()
            elif self.state == 'Inactive':
                self.activate()
        pl.draw()

    def remove_gate(self):
        self.disconnect()
        self.remove_artist()
        self.fig.canvas.draw()
        self.gateKeeper.remove_gate(self)

    def remove_artist(self):
        for artist in self.artistList:
            artist.remove()


class QuadGate(Filter):
    """ Defines a polygon gate. """
    def __init__(self, vert=None, channels=None, name=None, gateKeeper=None):
        Filter.__init__(self, vert, channels, name, gateKeeper)
        self.create_artist()
        self.set_state('Active')

    def connect(self):
        '''
        connect to all the events we need
        '''
        self.cidpress   = self.fig.canvas.mpl_connect('button_press_event', self.on_press)
        self.cidrelease = self.fig.canvas.mpl_connect('button_release_event', self.on_release)
        self.cidmotion  = self.fig.canvas.mpl_connect('motion_notify_event', self.on_mouse_motion)
        #self.cidpick    = self.fig.canvas.mpl_connect('pick_event', self.on_mouse_pick)
        self.cidkey     = self.fig.canvas.mpl_connect('key_press_event', self.on_keyboard_press)


    def create_artist(self):
        artistList = []
        vert = self.vert
        self.vline = self.ax.axvline(x=vert[0], **STYLE.ActiveQuadGate)
        self.hline = self.ax.axhline(y=vert[1], **STYLE.ActiveQuadGate)
        self.center = pl.Line2D([vert[0]], [vert[1]], picker=10, **STYLE.ActiveQuadGateCenter)
        self.ax.add_artist(self.center)
        self.artistList = [self.vline, self.hline, self.center]
        self.fig.canvas.draw()

    def on_press(self, event):
        print 'Quad Gate. Mouse motion: '
        print self
        if event.inaxes != self.ax: return

        if self.state == 'Active':
            if not self.contains(event):
                self.inactivate()
            else:
                self.set_state('Moving Vertix')


    def on_mouse_motion(self, event):
        print 'Quad Gate. Mouse motion: '
        print self
        #print self.state
        if self.state == 'Moving Vertix':
            self.vert = (event.xdata, event.ydata)
            self.draw()

    def on_release(self, event):
        if self.state == 'Moving Vertix':
            self.vline.set_xdata((event.xdata, event.xdata))
            self.hline.set_ydata((event.ydata, event.ydata))
            self.center.set_xdata([event.xdata])
            self.center.set_ydata([event.ydata])
            self.set_state('Active')
            pl.draw()

    def inactivate(self):
        self.set_state('Inactive')
        self.vline.update(STYLE.InactiveQuadGate)
        self.hline.update(STYLE.InactiveQuadGate)
        self.center.update(STYLE.InactiveQuadGateCenter)
        self.fig.canvas.draw()

    def activate(self):
        self.set_state('Active')
        self.vline.update(STYLE.ActiveQuadGate)
        self.hline.update(STYLE.ActiveQuadGate)
        self.center.update(STYLE.ActiveQuadGateCenter)
        self.fig.canvas.draw()

    def draw(self):
        xdata = self.vert[0]
        ydata = self.vert[1]
        self.vline.set_xdata((xdata, xdata))
        self.hline.set_ydata((ydata, ydata))
        self.center.set_xdata([xdata])
        self.center.set_ydata([ydata])
        pl.draw()

    def get_control_artist(self):
        return self.center

class PolygonGate(Filter):
    """ Defines a polygon gate. """
    def __init__(self, vert=None, channels=None, name=None, gateKeeper=None):
        Filter.__init__(self, vert, channels, name, gateKeeper)

        if vert is not None:
            self.vert = vert
        else:
            self.vert = []

        self.set_state('Creating Gate')

        self.lineToProposedVertix = None
        self.temporaryBorderLineList = []


    def connect(self):
        '''
        connect to all the events we need
        '''
        self.cidpress   = self.fig.canvas.mpl_connect('button_press_event', self.on_press)
        self.cidrelease = self.fig.canvas.mpl_connect('button_release_event', self.on_release)
        self.cidmotion  = self.fig.canvas.mpl_connect('motion_notify_event', self.on_mouse_motion)
        #self.cidpick    = self.fig.canvas.mpl_connect('pick_event', self.on_mouse_pick)
        self.cidkey     = self.fig.canvas.mpl_connect('key_press_event', self.on_keyboard_press)

    def get_control_artist(self):
        return self.poly

    def get_closest_vertix(self, currentCoordinate):
        """ Get closest vertix. """
        #for thisVertix in self.get_vertices()
        distancesList = [(euclid_distance(currentCoordinate, thisVertix), thisIndex, thisVertix) for thisIndex, thisVertix in enumerate(self.get_vertices())]
        distancesList.sort(key = lambda x : x[0])
        distance, closestVerticIndex, closestVertixPosition = distancesList[0]
        print 'Computing Closest'
        print distancesList[0]
        print closestVerticIndex
        return distance, closestVerticIndex, closestVertixPosition

    def add_vertix_to_growing_polygon(self, vertix):
        self.vert.append(vertix)
        if len(self.vert) > 1:
            lastLine = zip(self.vert[-2], self.vert[-1])
            self.temporaryBorderLineList.append(pl.Line2D(lastLine[0], lastLine[1], **STYLE.TemporaryPolygonGateBorderLine))
            self.ax.add_artist(self.temporaryBorderLineList[-1])

    def finish_drawing_polygon(self, vertix):
        self.vert.append(vertix)

        ## Remove artists used for helping with gate creation
        self.lineToProposedVertix.remove()

        for temporaryBorderLine in self.temporaryBorderLineList:
            temporaryBorderLine.remove()

        # Create the artist
        self.create_artist()

    def create_artist(self):
        ## Create polygon
        self.poly = pl.Polygon(self.vert, picker=15, **STYLE.ActivePolygonGate)
        self.ax.add_artist(self.poly)

        ## Create PolygonBorder
        x, y = zip(*self.poly.xy)
        self.polygonBorder = pl.Line2D(x[:-1], y[:-1], **STYLE.PolygonGateBorderLine)
        self.ax.add_artist(self.polygonBorder)

        self.artistList = [self.poly, self.polygonBorder]

        self.adjust_border()

    def get_vertices(self, transAxes=False):
        """ Return vertices in axis coordinates """
        ## TODO Fix a bug here to make sure selected points are close in axis space rather than data space.
        if transAxes:
            xy = self.poly.get_xy()
            inv = self.ax.transAxes.inverse()
            return inv.transform(xy)
        else:
            return self.poly.get_xy()

    def on_press(self, event):
        'on button press we will see if the mouse is over us and store some data'
        print 'mouse press'
        print self
        if event.inaxes != self.ax: return

        #if self.state == 'Inactive' and self.gateKeeper.state not in [STATE_GK.START_DRAWING, STATE_GK.KEEP_DRAWING]:
            #if self.contains(event):
                #self.activate()
        if self.state == 'Creating Gate':
            newVertix = (event.xdata, event.ydata)
            if event.button == MOUSE.leftClick:
                self.add_vertix_to_growing_polygon(newVertix)
            if event.button == MOUSE.rightClick:
                self.finish_drawing_polygon(newVertix)
                self.set_state('Active')
                self.gateKeeper.set_state(STATE_GK.WAITING)
        elif self.state == 'Active':
            if self.contains(event):
                print('contains the event.')
                self.info = self.get_closest_vertix((event.xdata, event.ydata))
                self.set_state('Moving Vertix')
            else:
                self.inactivate()

        self.fig.canvas.draw()

    def on_mouse_motion(self, event):
        'on motion we will move the rect if the mouse is over us'
        print self
        if self.state == 'Inactive':
            return
        elif self.state == 'Creating Gate':
            print 'mouse moving'
            lastVertix = self.vert[-1]
            potentialVertixPosition = (event.xdata, event.ydata)
            print potentialVertixPosition
            print lastVertix
            line_xydata = zip(lastVertix, potentialVertixPosition)

            if self.lineToProposedVertix is None:
                self.lineToProposedVertix = pl.Line2D(line_xydata[0], line_xydata[1])
                self.ax.add_artist(self.lineToProposedVertix)
            else:
                self.lineToProposedVertix.set_xdata(line_xydata[0])
                self.lineToProposedVertix.set_ydata(line_xydata[1])
            self.fig.canvas.draw()
        elif self.state == 'Moving Vertix':
            closestVertixIndex = self.info[1]

            numVertices = len(self.get_vertices())

            xy = self.poly.get_xy()
            if closestVertixIndex == 0 or closestVertixIndex == numVertices-1: # TODO needed because of unintuitive matplotlib behavior. first and last vertix to be the same
                xy[0] = (event.xdata, event.ydata)
                xy[-1] = (event.xdata, event.ydata)
            else:
                xy[closestVertixIndex] = (event.xdata, event.ydata)

            self.poly.set_xy(xy)
            self.adjust_border()

    def adjust_border(self):
        """ Method that implements relevant changes when the polygon is changed. """
        xy = self.poly.get_xy()

        self.polygonBorder.set_xdata(xy[:, 0])
        self.polygonBorder.set_ydata(xy[:, 1])

        #self.gateKeeper.grayout_all_points()
        #self.gateKeeper.highlight_points_inside_gate(self)

        self.fig.canvas.draw()

    def on_release(self, event):
        #util.raiseNotDefined()
        'on release we reset the press data'
        if self.state == 'Moving Vertix':
            self.set_state('Active')

    def on_keyboard_press(self, event):
        if event.key == 'i':
            self.inactivate()
        elif event.key == 'a':
            self.activate()
        elif event.key == 'd': # Delete gate if the gate is active
            if self.state == 'Active':
                self.remove_gate()

    def inactivate(self):
        self.set_state('Inactive')
        self.poly.update(STYLE.InactivePolygonGate)
        self.polygonBorder.set_visible(False)
        self.poly.figure.canvas.draw()

    def activate(self):
        self.set_state('Active')
        self.poly.update(STYLE.ActivePolygonGate)
        self.polygonBorder.set_visible(True)
        self.poly.figure.canvas.draw()

class GateKeeper():
    """ This will maintain a list of all the active gates. """

    def __init__(self, ax, fig, gateList=None):
        if gateList is not None: GateKeeper.gateList = gateList
        else: GateKeeper.gateList = []
        GateKeeper.current_channels = None

        self.data = None
        self.collection = None
        self.fig =  fig
        self.ax = ax
        self.set_state(STATE_GK.WAITING)
        self.connect()

        # For Quad Gate
        self.cursorWidget = None

    def connect(self):
        #self.cidrelease = self.fig.canvas.mpl_connect('button_release_event', self.on_release)
        #self.cidmotion  = self.fig.canvas.mpl_connect('motion_notify_event', self.on_mouse_motion)
        self.cidpress   = self.fig.canvas.mpl_connect('button_press_event',  self.on_mouse_press)
        self.cidkey     = self.fig.canvas.mpl_connect('key_press_event',  self.on_keyboard_press)
        self.cidpick    = self.fig.canvas.mpl_connect('pick_event', self.on_mouse_pick)

    def disconnect(self):
        'disconnect all the stored connection ids'
        ## TODO Define disconnect event properly
        self.fig.canvas.mpl_disconnect(self.cidpress)
        #self.fig.canvas.mpl_disconnect(self.cidrelease)
        self.fig.canvas.mpl_disconnect(self.cidmotion)
        self.fig.canvas.mpl_disconnect(self.cidpick)
        self.fig.canvas.mpl_disconnect(self.cidkey)

    def on_mouse_motion(self, event):
        """ Motion events. """
        print 'Gate Keeper state: ', self.state
        if self.state == STATE_GK.START_DRAWING_QUAD_GATE:
            if self.cursorWidget == None:
                self.cursorWidget = Cursor(self.ax)

    def on_mouse_press(self, event):
        """ Button press events. """
        print 'Mouse Press. Gate Keeper state: ', self.state
        if self.state == STATE_GK.WAITING:
            print 'Selecting gates...'
            # Quick and dirty code here. Can optimize

            ## Choose gate
            if len(GateKeeper.gateList) > 0:
                self.inactivate_all_gates()
                #activeGateList = [thisGate for thisGate in GateKeeper.gateList if thisGate.contains(event)]

                for thisGate in GateKeeper.gateList:
                    if thisGate.contains(event):
                        thisGate.activate()
                        self.bring_gate_to_top_layer(thisGate)
                        #if not thisGate.is_active():
                            #thisGate.activate()
                            #self.grayout_all_points()
                            #self.highlight_points_inside_gate(thisGate)
#
                            #for gateToInactivate in activeGateList:
                                #if gateToInactivate is not thisGate:
                                    #gateToInactivate.inactivate()
#
                        #break

                # Now let's put the active gate on the top layer...
                self.bring_gate_to_top_layer(thisGate)
                print 'Gate on top layer is: '
                print thisGate
        elif self.state == STATE_GK.START_DRAWING:
            print 'Creating a polygon gate'
            self.inactivate_all_gates()
            gate = PolygonGate(vert=None, channels=GateKeeper.current_channels, name='Polygon Gate', gateKeeper=self)
            self.add_gate(gate)
            gate.on_press(event)
            self.set_state(STATE_GK.KEEP_DRAWING)

        elif self.state == STATE_GK.START_DRAWING_QUAD_GATE:
            self.inactivate_all_gates()
            quadGate = QuadGate(vert=(event.xdata, event.ydata), channels=GateKeeper.current_channels, name='Quad Gate', gateKeeper=self)
            self.add_gate(quadGate)
            self.cursorWidget = None
            self.set_state(STATE_GK.WAITING)

    def change_axis(self, event):
        ''' Function controls the x and y labels. Upon clicking on them the user can change what is plotted on the
            x and y axis.
        '''
        if event.artist == self.xlabelArtist:
            userchoice = dialogs.select_option_dialog('Select channel for x axis', self.data.channels)

            if userchoice is None:
                return

            index, value = userchoice
            GateKeeper.current_channels[0] = value

        elif event.artist == self.ylabelArtist:
            #y_options = list(self.data.channels)
            #y_options.append('Counts')
            userchoice = dialogs.select_option_dialog('Select channel for y axis', self.data.channels)

            if userchoice is None:
                return

            index, value = userchoice
            GateKeeper.current_channels[1] = value

        self.show_visible_gates()
        self.plot_data()

    def show_visible_gates(self):
        for thisGate in GateKeeper.gateList:
            print thisGate.channels
            print GateKeeper.current_channels
            if thisGate.channels == GateKeeper.current_channels:
                thisGate.set_visible(True)
            else:
                thisGate.set_visible(False)
        pl.draw()

    def inactivate_all_gates(self):
        for gate in GateKeeper.gateList:
            gate.inactivate()

    def on_mouse_pick(self, event):
        """ Event picker """
        if event.artist == self.xlabelArtist or event.artist == self.ylabelArtist:
            ### In case we want to change the axis
            self.change_axis(event)

    def on_keyboard_press(self, event):
        if event.key == 'c':
            self.set_state(STATE_GK.START_DRAWING)
        elif event.key == 'w':
            print GateKeeper.gateList

    def add_gate(self, gate):
        """ Adds the current gate to the gate list. """
        GateKeeper.gateList.insert(0, gate)#append(gate)

    def bring_gate_to_top_layer(self, gate):
        GateKeeper.gateList.remove(gate)
        GateKeeper.gateList.insert(0, gate)

    def remove_gate(self, gate):
        GateKeeper.gateList.remove(gate)
        del gate

    def get_active_gate(self):
        for thisGate in GateKeeper.gateList:
            if thisGate.is_active():
                print 'Active gate is: '
                print thisGate
                return thisGate

    def set_state(self, state):
        """ TODO Remove the handling of deleting gates here. """
        if state == STATE_GK.DELETE_GATE:
            activeGate = self.get_active_gate()
            if activeGate:
                activeGate.remove_gate()
            state = STATE_GK.WAITING

        self.ax.set_title(state)
        self.fig.canvas.draw()
        self.state = state

    def plot_data(self, numpoints=1000):
        # TODO fix transform
        #numData = numpy.shape((self.data))[0]
        #facecolors = [STYLE.DATUM_OUT_COLOR for d in range(numData)]
#
        #index1, index2 = GateKeeper.current_channels
#
        data = self.data
        #channel_names = [data.channels[index] for index in GateKeeper.current_channels]


        ax = self.ax
        ax.cla()

        channels = GateKeeper.current_channels

        if channels[0] == channels[1]:
            plotFCM(data, channels[0], transform=(None, ), ax=ax)
            xlabel = GateKeeper.current_channels[0]
            ylabel = 'Counts'

            self.xlabelArtist = ax.set_xlabel(xlabel, picker=5)
            self.ylabelArtist = ax.set_ylabel(ylabel, picker=5)
        else:
            plotFCM(data, GateKeeper.current_channels, transform=(None, None), ax=ax, plot2d_type='hist2d')
            xlabel = GateKeeper.current_channels[0]
            ylabel = GateKeeper.current_channels[1]

            self.xlabelArtist = ax.set_xlabel(xlabel, picker=5)
            self.ylabelArtist = ax.set_ylabel(ylabel, picker=5)

        #self.dataxy = self.data[:1000, [index1, index2]]
        ##
        #if self.collection is not None:
            #self.collection.remove()
        ##
        #self.collection = RegularPolyCollection(ax.figure.dpi, 6, sizes=(10,), alpha=0.8, facecolors=facecolors, offsets = self.dataxy, transOffset = ax.transData)
        #self.ax.add_collection(self.collection)
        #
        ##self.ax.relim()
        ##self.ax.autoscale_view(True, True, True)
        #xmin = min(self.data[:, index1])
        #xmax = max(self.data[:, index1])
        #ymin = min(self.data[:, index2])
        #ymax = max(self.data[:, index2])
        #
        #ax.set_xlim(xmin, xmax)
        #ax.set_ylim(ymin, ymax)
        #
        #xlabel = self.data.channels[index1]
        #ylabel = self.data.channels[index2]

        pl.draw()

    def grayout_all_points(self):
        """ gray out all points """
        return
        if self.data is None: return

        numDataPoints = len(self.dataxy)

        facecolors = self.collection.get_facecolors()
        for i in range(numDataPoints):
            facecolors[i] = STYLE.DATUM_OUT_COLOR
        self.fig.canvas.draw()

    def highlight_points_inside_gate(self, gate):
        """ Locates the points inside the given polygon vertices. """
        return # Does nothing atm
        if self.data is None: return

        numDataPoints = len(self.dataxy)

        print 'Data points length'
        print numDataPoints

        if isinstance(gate, PolygonGate):
            facecolors = self.collection.get_facecolors()
            inPointsIndexes = numpy.nonzero(points_inside_poly(self.dataxy, gate.get_vertices()))[0]
            for i in inPointsIndexes:
                facecolors[i] = STYLE.DATUM_IN_COLOR

        self.fig.canvas.draw()

    #def set_current_channels(self, channel_names=None):
        #""" Note potentially confusing I am going back between names and indexes. """
        #if

    def load_fcs(self, filepath=None):
        ''' '''
        if filepath is None:
            filepath = dialogs.open_file_dialog('Select an FCS file to load', 'FCS files (*.fcs)|*.fcs')
        if filepath is not None:
            self.data = loadFCS(filepath)
            if GateKeeper.current_channels == None:
                GateKeeper.current_channels = self.data.channels[0:2] # Assigns first two channels by default if none have been specified yet.
            self.plot_data()

    def load_gates(self, filepath=None):
        ''' '''
        pass
    def save_gates(self, filepath=None):
        ''' '''
        pass
