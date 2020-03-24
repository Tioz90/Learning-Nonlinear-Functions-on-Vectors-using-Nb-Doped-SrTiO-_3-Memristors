import numpy as np


def sparsity_measure( vector ):  # Gini index
    # Max sparsity = 1 (single 1 in the vector)
    v = np.sort( np.abs( vector ) )
    n = v.shape[ 0 ]
    k = np.arange( n ) + 1
    l1norm = np.sum( v )
    summation = np.sum( (v / l1norm) * ((n - k + 0.5) / n) )
    
    return 1 - 2 * summation


def mse( sim, x, y, learning_time, simulation_step ):
    return (
            np.square( sim.data[ x ][ int( learning_time / simulation_step ): ] -
                       sim.data[ y ][ int( learning_time / simulation_step ): ] )
    ).mean()


def plot_network( model ):
    from nengo_extras import graphviz
    
    net = graphviz.net_diagram( model )
    from graphviz import Source
    
    s = Source( net, filename="./net.png", format="png" )
    s.view()


def plot_pre_post( sim, pre, post, input, error=None, time=None ):
    import datetime
    import matplotlib.pyplot as plt
    
    num_subplots = 1
    if error:
        num_subplots = 2
    fix, axes = plt.subplots( num_subplots, 1, sharex=True, sharey=True, squeeze=False )
    # axes = axes.flatten()
    # plot input, neural representations and error
    # plt.suptitle( datetime.datetime.now().strftime( '%H:%M:%S %d-%m-%Y' ) )
    axes[ 0, 0 ].plot( sim.trange(), sim.data[ input ], c="k", label="Input" )
    axes[ 0, 0 ].plot( sim.trange(), sim.data[ pre ], c="b", label="Pre" )
    axes[ 0, 0 ].plot( sim.trange(), sim.data[ post ], c="g", label="Post" )
    if error:
        axes[ 1, 0 ].plot( sim.trange(), error, c="r", label="Error" )
    if time:
        for ax in axes:
            ax[ 0 ].axvline( x=time, c="k" )
            # ax[ 0 ].annotate( "Training end", xy=(time, np.amax( sim.data[ input ] )), xycoords='data' )
    plt.legend( loc='best' )
    plt.show()


def plot_ensemble_spikes( sim, name, ensemble, input=None, time=None ):
    import datetime
    from nengo.utils.matplotlib import rasterplot
    import matplotlib.pyplot as plt
    
    # plot spikes from pre
    plt.figure()
    # plt.suptitle( datetime.datetime.now().strftime( '%H:%M:%S %d-%m-%Y' ) )
    fig, ax1 = plt.subplots()
    ax1 = plt.subplot( 1, 1, 1 )
    rasterplot( sim.trange(), sim.data[ ensemble ], ax1 )
    ax1.set_xlim( 0, max( sim.trange() ) )
    ax1.set_ylabel( 'Neuron' )
    ax1.set_xlabel( 'Time (s)' )
    if input:
        ax2 = plt.twinx()
        ax2.plot( sim.trange(), sim.data[ input ], c="k" )
    if time:
        time = int( time )
        for t in range( time ):
            plt.axvline( x=t, c="k" )
    plt.title( name + " neural activity" )
    plt.show()