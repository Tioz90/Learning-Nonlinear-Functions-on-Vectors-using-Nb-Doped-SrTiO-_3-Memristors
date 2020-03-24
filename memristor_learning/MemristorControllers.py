import numpy as np

from memristor_learning.MemristorModels import *


class MemristorController:
    def __init__( self, model, learning_rule, in_size, out_size, dimensions, dt=0.001, logging=True ):
        self.memristor_model = model
        
        self.input_size = in_size
        self.pre_dimensions = dimensions[ 0 ]
        self.post_dimensions = dimensions[ 1 ]
        self.output_size = out_size
        
        self.dt = dt
        
        self.weights = None
        self.memristors = None
        
        self.learning_rule = learning_rule
        self.learning_rule.input_size = in_size
        self.learning_rule.output_size = out_size
        self.learning_rule.logging = logging
        
        # save for analysis
        self.logging = logging
        self.weight_history = [ ]
        self.error_history = [ ]


class MemristorArray( MemristorController ):
    def __init__( self, model, learning_rule, in_size, out_size, dimensions ):
        super().__init__( model, learning_rule, in_size, out_size, dimensions )
        
        # to hold future weights
        self.weights = np.zeros( (self.output_size, self.input_size), dtype=np.float )
        
        # create memristor array that implement the weights
        self.memristors = np.empty( (self.output_size, self.input_size), dtype=MemristorAnouk )
        for i in range( self.output_size ):
            for j in range( self.input_size ):
                self.memristors[ i, j ] = self.memristor_model()
                self.weights[ i, j ] = self.memristors[ i, j ].get_state( value="conductance", scaled=True )
        
        self.learning_rule.weights = self.weights
        self.learning_rule.memristors = self.memristors
    
    def __call__( self, t, x ):
        ret = self.learning_rule( t, x )
        
        if self.logging:
            err = self.learning_rule.get_error_signal()
            if err is not None:
                self.error_history.append( err )
            
            self.save_state()
            self.weight_history.append( self.weights.copy() )
        
        return ret
    
    def get_components( self ):
        return self.memristors.flatten()
    
    def save_state( self ):
        for j in range( self.output_size ):
            for i in range( self.input_size ):
                self.memristors[ j, i ].save_state()
    
    def plot_state( self, sim, value, err_probe=None, combined=False, time=None ):
        import datetime
        import matplotlib.pyplot as plt
        from matplotlib.pyplot import cm
        from nengo.utils.matplotlib import rasterplot
        
        # plot memristor resistance and error
        plt.figure()
        # plt.suptitle( datetime.datetime.now().strftime( '%H:%M:%S %d-%m-%Y' ) )
        if not combined:
            fig, axes = plt.subplots()
        if combined:
            fig, axes = plt.subplots( self.output_size, self.input_size )
        plt.xlabel( "Post neurons on rows\nPre neurons on columns" )
        plt.ylabel( "Post neurons on columns" )
        # fig.suptitle( "Memristor " + value, fontsize=16 )
        colour = iter( cm.rainbow( np.linspace( 0, 1, self.memristors.size ) ) )
        for i in range( self.memristors.shape[ 0 ] ):
            for j in range( self.memristors.shape[ 1 ] ):
                c = next( colour )
                if not combined:
                    self.memristors[ i, j ].plot_state( value, i, j, sim.trange(), axes, c, combined )
                    if time:
                        time = int( time )
                        for t in range( time ):
                            axes.axvline( x=t, c="k" )
                if combined:
                    self.memristors[ i, j ].plot_state( value, i, j, sim.trange(), axes[ i, j ], c, combined )
                    if time:
                        time = int( time )
                        for t in range( time ):
                            axes[ i, j ].axvline( x=t, c="k" )
        if err_probe:
            ax2 = plt.twinx()
            ax2.plot( sim.trange(), sim.data[ err_probe ], c="r", label="Error" )
        plt.show()
    
    def plot_weight_matrix( self, time ):
        import matplotlib.pyplot as plt
        
        weights_at_time = self.weight_history[ int( time / self.dt ) ]
        
        fig, ax = plt.subplots()
        
        ax.matshow( weights_at_time, cmap=plt.cm.Blues )
        max_weight = np.amax( weights_at_time )
        min_weight = np.amin( weights_at_time )
        
        for i in range( weights_at_time.shape[ 0 ] ):
            for j in range( weights_at_time.shape[ 1 ] ):
                c = round( (weights_at_time[ j, i ] - min_weight) / (max_weight - min_weight), 2 )
                ax.text( i, j, str( c ), va='center', ha='center' )
        plt.title( "Weights at t=" + str( time ) )
        plt.show()
    
    def get_history( self, select ):
        if select == "weight":
            return self.weight_history
        if select == "error":
            return self.error_history